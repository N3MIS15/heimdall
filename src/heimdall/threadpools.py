from collections import deque
from collections import namedtuple
import threading
import logging

log = logging.getLogger("heimdall.threadpools")

class Runnable(object):
	def run(self, *args, **kwargs):
		pass

class Callback(object):
	def onDone(self, runnable, error, result):
		pass

class ThreadPool(object):
	def append(self, runnable, callback, *args, **kwargs):
		pass

WorkItem = namedtuple("WorkItem", [ "runnable", "callback", "args", "kwargs" ])

def safe_run(runnable, args, kwargs):
	if callable(runnable):
		return runnable(*args, **kwargs)
	else:
		return runnable.run(*args, **kwargs)

def safe_callback(callback, runnable, error, result):
	if callable(callback):
		callback(runnable, error, result)
	else:
		callback.onDone(runnable, error, result)

def safe_execute(wi):
	error = None
	result = None
	try:
		log.debug("Running %s in %s with args %s and kwargs %s", wi.runnable, threading.current_thread(), wi.args, wi.kwargs)
		result = safe_run(wi.runnable, wi.args, wi.kwargs)
	except Exception as e:
		error = e
		log.exception("Failure on run of %s with args %s and kwargs %s", str(wi.runnable), json.dumps(wi.args), json.dumps(wi.kwargs))
	finally:
		safe_callback(wi.callback, wi.runnable, error, result)

class ThreadedWorker(threading.Thread):
	def __init__(self, owner):
		super(ThreadedWorker, self).__init__()
		self.owner = owner
		self.start()

	def run(self):
		wi = self.owner.getNextWorkItem()

		while wi:
			safe_execute(wi)

			wi = self.owner.getNextWorkItem()

		self.owner.onDone(self)

class MainloopThreadPool(object):
	def __init__(self):
		self.condition = threading.Condition()
		self.queue = deque()
		self.run = True

	def append(self, runnable, callback, *args, **kwargs):
		self.condition.acquire()
		self.queue.append(WorkItem(runnable, callback, args, kwargs))
		self.condition.notifyAll()
		self.condition.release()

	def quit(self):
		log.debug("Quiting threadpool")
		self.condition.acquire()
		self.run = False
		self.condition.notifyAll()
		self.condition.release()

	def join(self):
		self.condition.acquire()
		while self.run:
			if len(self.queue) > 0:
				wi = self.queue.popleft()
				safe_execute(wi)
			else:
				try:
					self.condition.wait()
				except Exception as e:
					log.exception("Failure while waiting")
					raise e
		self.condition.release()

class SingleThreadedThreadPool(object):
	def __init__(self):
		self.condition = threading.Condition()
		self.queue = deque()
		self.run = True
		self.worker = None

	def append(self, runnable, callback, *args, **kwargs):
		with self.condition:
			self.queue.append(WorkItem(runnable, callback, args, kwargs))
			if self.worker == None:
				self.worker = ThreadedWorker(self)
			self.condition.notifyAll()

	def getNextWorkItem(self):
		with self.condition:
			wi = None
			if len(self.queue) > 0 and self.run:
				wi = self.queue.popleft()
			self.condition.notifyAll()
			return wi

	def onDone(self, worker):
		log.debug("Removing worker from threadpool")
		with self.condition:
			self.worker = None
			self.condition.notifyAll()

	def quit(self):
		log.debug("Quiting threadpool")
		with self.condition:
			self.run = False
			self.condition.notifyAll()

	def join(self):
		with self.condition:
			while self.run and self.worker and len(self.queue) > 0:
				self.condition.wait()

class OptimisticThreadPool(object):
	def __init__(self, numberWorkers):
		self.condition = threading.Condition()
		self.queue = deque()
		self.acceptNewTasks = True
		self.numberWorkers = numberWorkers
		self.workers = list()

	def append(self, runnable, callback, *args, **kwargs):
		with self.condition:
			if self.acceptNewTasks:
				self.queue.append(WorkItem(runnable, callback, args, kwargs))
				if len(self.workers) < self.numberWorkers:
					self.workers.append(ThreadedWorker(self))
				self.condition.notifyAll()

	def getNextWorkItem(self):
		with self.condition:
			wi = None
			if len(self.queue) > 0:
				wi = self.queue.popleft()
			self.condition.notifyAll()
			return wi

	def onDone(self, worker):
		with self.condition:
			self.workers.remove(worker)
			self.condition.notifyAll()

	def join(self):
		with self.condition:
			while len(self.workers) > 0 and len(self.queue) > 0:
				self.condition.wait()

	def quit(self):
		log.debug("Quiting threadpool")
		with self.condition:
			self.queue = deque()
			self.acceptNewTasks = False
			self.condition.notifyAll()
