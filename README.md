# pyworkflow.blinker

## blinker backend for pyworkflow

[pyworkflow](http://github.com/pyworkflow/pyworkflow) supports the easy implementation of workflows, and handling the
execution of workflow processes, across multiple backends. This is the
backend for pyworkflow that supports [blinker](http://pythonhosted.org/blinker/) signals.

## Usage

BlinkerBackend wraps around any other backend and emits [blinker](http://pythonhosted.org/blinker/) signals on
important runtime events on activities and decisions.

````python
from pyworkflow.memory import MemoryBackend
from pyworkflow.blinker import BlinkerBackend
from pyworkflow.managed import Manager

backend = BlinkerBackend(MemoryBackend())
manager = Manager(backend=backend)

# listen to process started signal
def process_started(sender, **kwargs):
	print 'Started %s' % kwargs['process']

BlinkerBackend.on_process_started.connect(process_started)
````

## About

### License

pyworkflow.blinker is under the MIT License.

### Contact

pyworkflow.blinker is written by [Willem Bult](https://github.com/willembult).

Project Homepage: [https://github.com/pyworkflow/pyworkflow.blinker](https://github.com/pyworkflow/pyworkflow.blinker)

Feel free to contact me. But please file issues in github first. Thanks!
