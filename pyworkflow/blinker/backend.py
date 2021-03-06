from blinker import Signal

from pyworkflow.backend import Backend
from pyworkflow.decision import *
from pyworkflow.activity import *

class BlinkerBackend(Backend):
    # Blinker signals
    on_complete_decision_task = Signal()
    on_complete_activity_task = Signal()

    on_activity_scheduled = Signal()
    on_activity_started = Signal()
    on_activity_completed = Signal()
    on_activity_canceled = Signal()
    on_activity_failed = Signal()
    on_activity_timedout = Signal()

    on_process_started = Signal()
    on_process_completed = Signal()
    on_process_canceled = Signal()
    on_process_signaled = Signal()
    

    def __init__(self, parent):
        self.parent = parent

    # Pipe through most (non-event-generating) requests directly to parent backend

    def register_workflow(self, *args, **kwargs):
        return self.parent.register_workflow(*args, **kwargs)

    def register_activity(self, *args, **kwargs):
        return self.parent.register_activity(*args, **kwargs)

    def process_by_id(self, *args, **kwargs):
        return self.parent.process_by_id(*args, **kwargs)

    def processes(self, *args, **kwargs):
        return self.parent.processes(*args, **kwargs)

    def poll_activity_task(self, *args, **kwargs):
        return self.parent.poll_activity_task(*args, **kwargs)

    def poll_decision_task(self, *args, **kwargs):
        task = self.parent.poll_decision_task(*args, **kwargs)
        if task:
            for event in task.process.unseen_events():
                # check if this is a child process id (first time we can get id)
                if event.type == 'process_started' and task.process.parent:
                    BlinkerBackend.on_process_started.send(self, process=task.process, process_id=task.process.id, parent_process_id=task.process.parent)
                # check if any activities have timed out
                if hasattr(event, 'result') and isinstance(event.result, ActivityTimedOut):
                    BlinkerBackend.on_activity_timedout.send(self, activity_execution=event.activity_execution, details=event.result.details)
        return task
    
    def heartbeat_activity_task(self, *args, **kwargs):
        return self.parent.heartbeat_activity_task(*args, **kwargs)

    # For the events we're interested in, emit signals

    def start_process(self, process):
        ret = self.parent.start_process(process)
        BlinkerBackend.on_process_started.send(self, process=process, process_id=ret)
        return ret        
    
    def signal_process(self, process_id, signal, data=None):
        ret = self.parent.signal_process(process_id, signal, data=data)
        
        BlinkerBackend.on_process_signaled.send(self, process_id=process_id, signal=signal, data=data)
        return ret        

    def cancel_process(self, process_id, details=None):
        ret = self.parent.cancel_process(process_id, details=details)
        
        BlinkerBackend.on_process_canceled.send(self, process_id=process_id, details=details)
        return ret

    def decision_signal(self, decision):
        mapping = {
            ScheduleActivity: BlinkerBackend.on_activity_scheduled,
            CancelActivity: BlinkerBackend.on_activity_canceled,
            CompleteProcess: BlinkerBackend.on_process_completed,
            CancelProcess: BlinkerBackend.on_process_canceled,
            StartChildProcess: None, # don't have the id yet
            Timer: None
        }

        return mapping[decision.__class__]

    def activity_result_signal(self, result):
        mapping = {
            ActivityCompleted: BlinkerBackend.on_activity_completed,
            ActivityCanceled: BlinkerBackend.on_activity_canceled,
            ActivityFailed: BlinkerBackend.on_activity_failed,
            ActivityTimedOut: BlinkerBackend.on_activity_timedout
        }

        return mapping[result.__class__]

    def complete_decision_task(self, task, decisions):
        ret = self.parent.complete_decision_task(task, decisions)

        BlinkerBackend.on_complete_decision_task.send(self, task=task, decisions=decisions)
        
        for decision in decisions if type(decisions) == list else [decisions]:
            signal = self.decision_signal(decision)
            if not signal:
                continue

            args = {
                'schedule_activity': lambda: {'process': task.process, 'activity_execution': ActivityExecution(decision.activity, decision.id, decision.input)},
                'complete_process': lambda: {'process': task.process, 'process_id': task.process.id, 'result': decision.result},
                'cancel_process': lambda: {'process': task.process, 'process_id': task.process.id, 'details': decision.details},
                'cancel_activity': lambda: {'process': task.process, 'activity_id': decision.id},
            }

            signal.send(self, **args[decision.type]())

        return ret        

    def complete_activity_task(self, task, result=None):
        ret = self.parent.complete_activity_task(task, result=result)

        BlinkerBackend.on_complete_activity_task.send(self, task=task, result=result)

        args = {
            'completed': lambda: {'result': result.result},
            'canceled': lambda: {'details': result.details},
            'failed': lambda: {'reason': result.reason, 'details': result.details},
            'timedout': lambda: {'details': result.details}
        }

        signal = self.activity_result_signal(result)
        signal.send(self, activity_execution=task.activity_execution, process_id=task.process_id, **args[result.type]())
        
        return ret
