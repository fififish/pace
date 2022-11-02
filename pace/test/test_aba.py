#!/usr/bin/python
__author__ = 'sisi'

import gevent
import random
import os
import time
import math

from gevent.event import Event
from gevent.queue import Queue

from ..core.utils import initiateThresholdSig
from ..core.broadcasts import shared_coin,binary_consensus

from ..commoncoin.thresprf import dealer


def simple_broadcast_router(N, maxdelay=0.005, seed=None):
    """Builds a set of connected channels, with random delay
    @return (receives, sends)
    """
    rnd = random.Random(seed)
    #if seed is not None: print 'ROUTER SEED: %f' % (seed,)
    
    queues = [Queue() for _ in range(N)]
    _threads = []

    def makeBroadcast(i):
        def _send(j, o):
            delay = rnd.random() * maxdelay
            #print 'SEND   %8s [%2d -> %2d] %2.1f' % (o[0], i, j, delay*1000), o[1:]
            gevent.spawn_later(delay, queues[j].put, (i,o))
            #queues[j].put((i, o))
        def _bc(o):
            #print 'BCAST  %8s [%2d ->  *]' % (o[0], i), o[1]
            for j in range(N): _send(j, o)
        return _bc

    def makeRecv(j):
        def _recv():
            (i,o) = queues[j].get()
            #print 'RECV %8s [%2d -> %2d]' % (o[0], i, j)
            return (i,o)
        return _recv
        
    return ([makeBroadcast(i) for i in range(N)],
            [makeRecv(j)      for j in range(N)])

### Test binary agreement with boldyreva coin
def _make_coins(sid, N, f, seed):
    # Generate keys
    rnd = random.Random(seed)
    router_seed = rnd.random()
    sends, recvs = simple_broadcast_router(N, seed=seed)
    coins = [shared_coin(sid, i, N, f, sends[i], recvs[i]) for i in range(N)]
    return coins

def _test_binaryagreement(options,N=4, f=1, seed=None):
    # Generate keys
    sid = 'sidA'
    # Test everything when runs are OK
    #if seed is not None: print 'SEED:', seed
    rnd = random.Random(seed)

    initiateThresholdSig(open(options.threshold_keys, 'r').read())

    # Instantiate the common coin
    #coins_seed = rnd.random()
    #coins = _make_coins(sid+'COIN', N, f, coins_seed)

    # Router
    router_seed = rnd.random()
    sends, recvs = simple_broadcast_router(N, seed=seed)

    threads = []
    inputs = []
    outputs = []

    for i in range(N):
        #inputs.append(Queue())
        #outputs.append(Queue())
        inputs.append(random.randrange(0,2))
        outputs.
        
        t = gevent.spawn(binary_consensus, sid, i, N, f, 
                         inputs[i].get, outputs[i].put_nowait, sends[i], recvs[i])
        threads.append(t)

    for i in range(N):
        inputs[i].put(random.randint(0,1))
    #gevent.killall(threads[N-f:])
    #gevent.sleep(3)
    #for i in range(N-f, N):
    #    inputs[i].put(0)
    try:
        outs = [outputs[i].get() for i in range(N)]
        assert len(set(outs)) == 1
        try: gevent.joinall(threads)
        except gevent.hub.LoopExit: pass
    except KeyboardInterrupt:
        gevent.killall(threads)
        raise

def test_binaryagreement(options):
    for i in range(5): _test_binaryagreement(options,seed=i)



if __name__ == '__main__':
    print "Testing binary consensus"

    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-e", "--ecdsa-keys", dest="ecdsa",
                      help="Location of ECDSA keys", metavar="KEYS")
    parser.add_option("-k", "--threshold-keys", dest="threshold_keys",
                      help="Location of threshold signature keys", metavar="KEYS")

    (options, args) = parser.parse_args()

    test_binaryagreement(options)