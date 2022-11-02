from gevent import monkey
monkey.patch_all()

import gevent
from gevent import Greenlet
from gevent.queue import Queue
import random
from random import Random

from ..core.utils import initiateThresholdSig

from ..core.broadcasts import bv_broadcast, cobalt_binary_consensus, binary_consensus, pace_binary_consensus, pace_biased_binary_consensus, pace_biased_binary_consensus_trigger, mv84consensus, globalState,decision, currentrounds
from ..core.utils import bcolors,mylog,getKeys
from ..commoncoin.thresprf_gipc import initialize as initializeGIPC
import time

# Run the BV_broadcast protocol with no corruptions and uniform random message delays
def random_delay_broadcast1(inputs, t):
    maxdelay = 0.01

    N = len(inputs)
    buffers = map(lambda _: Queue(1), inputs)

    # Instantiate the "broadcast" instruction
    def makeBroadcast(i):
        def _broadcast(v):
            def _deliver(j):
                buffers[j].put((i,v))
            for j in range(N): 
                Greenlet(_deliver, j).start_later(random.random()*maxdelay)
        return _broadcast

    def makeOutput(i):
        def _output(v):
            print '[%d]' % i, 'output:', v
        return _output
        
    ts = []
    for i in range(N):
        bc = makeBroadcast(i)
        recv = buffers[i].get
        outp = makeOutput(i)
        inp = bv_broadcast(i, N, t, bc, recv, outp)
        th = Greenlet(inp, inputs[i])
        th.start_later(random.random()*maxdelay)
        ts.append(th)

    try:
        gevent.joinall(ts)
    except gevent.hub.LoopExit: pass


# Run the BV_broadcast protocol with no corruptions and uniform random message delays
def random_delay_sharedcoin_dummy(N, t):
    maxdelay = 0.01

    buffers = map(lambda _: Queue(1), range(N))

    # Instantiate the "broadcast" instruction
    def makeBroadcast(i):
        def _broadcast(v):
            def _deliver(j):
                buffers[j].put((i,v))
            for j in range(N): 
                Greenlet(_deliver, j).start_later(random.random()*maxdelay)
        return _broadcast

    def _run(i, coin):
        # Party i, continue to run the shared coin
        r = 0
        while r < 5:
            gevent.sleep(random.random() * maxdelay)
            print '[',i,'] at round ', r
            b = next(coin)
            print '[',i,'] bit[%d]:'%r, b
            r += 1
        print '[',i,'] done'
        
    ts = []
    for i in range(N):
        bc = makeBroadcast(i)
        recv = buffers[i].get
        coin = shared_coin_dummy(i, N, t, bc, recv)
        th = Greenlet(_run, i, coin)
        th.start_later(random.random() * maxdelay)
        ts.append(th)

    try:
        gevent.joinall(ts)
    except gevent.hub.LoopExit: pass

# Run the BV_broadcast protocol with no corruptions and uniform random message delays
def random_delay_binary_consensus(N, t, inputs, version):
    instance = Random()
    instance.seed(123123)
    maxdelay = 0.01

    buffers = map(lambda _: Queue(1), range(N))
    random_delay_binary_consensus.msgCount = 0
    # Instantiate the "broadcast" instruction
    def makeBroadcast(i):
        def _broadcast(v):
            def _deliver(j):
                random_delay_binary_consensus.msgCount += 1
                tmpCount = random_delay_binary_consensus.msgCount
                mylog(bcolors.OKGREEN + "MSG: [%d] -[%d]-> [%d]: %s" % (i, tmpCount, j, repr(v)) + bcolors.ENDC)
                buffers[j].put((i, v))
                mylog(bcolors.OKGREEN + "     [%d] -[%d]-> [%d]: Finish" % (i, tmpCount, j) + bcolors.ENDC)
            for j in range(N):
                Greenlet(_deliver, j).start_later(random.random()*maxdelay)
        return _broadcast

    ts = []
    total = 0

    
    if version == 1:
        print "BEAT-MMR"
    elif version == 2:
        print "ACE"
    elif version == 3:
        print "PACE"
    elif version == 4:
        print "BEAT-COBALT"

    for i in range(N):
        bc = makeBroadcast(i)
        recv = buffers[i].get
        vi = inputs[i]  #random.randint(0, 1)
        total = total + vi
        decideChannel = Queue(1)
        if version==1: #beat0 from MMR
            th = Greenlet(binary_consensus, instance, i, N, t, vi, decideChannel, bc, recv)
        elif version == 2: #ACE from Pillar binary consensus
            th = Greenlet(pace_binary_consensus, instance, i, N, t, vi, 2, decideChannel, bc, recv)
        elif version == 3: #PACE from Pisa binary consensus
            th = Greenlet(pace_biased_binary_consensus, instance, i, N, t, vi, 2, decideChannel, bc, recv)
        elif version == 4: #beat-cobalt
            th = Greenlet(cobalt_binary_consensus, instance, i, N, t, vi, decideChannel, bc, recv)
            
        th.start_later(random.random() * maxdelay)
        ts.append(th)

    gevent.joinall(ts)


    for key, item in globalState.items():
        if item != globalState[0]:
            mylog(bcolors.FAIL + 'Bad Concensus!' + bcolors.ENDC)

    print "?", globalState


# Run the BV_broadcast protocol with no corruptions and uniform random message delays
def random_delay_multivalue_consensus(N, t, inputs):
    maxdelay = 0.01

    msgThreads = []

    buffers = map(lambda _: Queue(1), range(N))

    random_delay_multivalue_consensus.msgCount = 0
    # Instantiate the "broadcast" instruction
    def makeBroadcast(i):
        def _broadcast(v):
            def _deliver(j):
                random_delay_multivalue_consensus.msgCount += 1
                tmpCount = random_delay_multivalue_consensus.msgCount
                mylog(bcolors.OKGREEN + "MSG: [%d] -[%d]-> [%d]: %s" % (i, tmpCount, j, repr(v)) + bcolors.ENDC)
                buffers[j].put((i,v))
                mylog(bcolors.OKGREEN + "     [%d] -[%d]-> [%d]: Finish" % (i, tmpCount, j) + bcolors.ENDC)

            for j in range(N):
                g = Greenlet(_deliver, j)
                g.start_later(random.random()*maxdelay)
                msgThreads.append(g)  # Keep reference
        return _broadcast

    ts = []
    #cid = 1
    for i in range(N):
        bc = makeBroadcast(i)
        recv = buffers[i].get
        vi = inputs[i]
        th = Greenlet(mv84consensus, i, N, t, vi, bc, recv)
        th.start_later(random.random() * maxdelay)
        ts.append(th)

    try:
        gevent.joinall(ts)
    except gevent.hub.LoopExit: # Manual fix for early stop
        agreed = ""
        for key, value in globalState.items():
            if globalState[key] != "":
                agreed = globalState[key]
        for key,  value in globalState.items():
            if globalState[key] == "":
                globalState[key] = agreed
            if globalState[key] != agreed:
                print "Consensus Error"


    print globalState

if __name__=='__main__':
    print "[ =========== ]"
    print "Testing binary consensus..."


    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-k", "--threshold-keys", dest="threshold_keys",
                      help="Location of threshold signature keys", metavar="KEYS")
    
    parser.add_option("-v", "--version", dest="version",
                      help="Protocol version, 1 for MMR, 2 for Pillar, 3 for Pisa (RABA of Pillar), 4 for Cobalt", metavar="VERSION")

    parser.add_option("-n", "--number", dest="number",
                      help="number of replicas", metavar="NUMBER")

    parser.add_option("-t", "--failure", dest="failure",
                      help="number of faulty replicas", metavar="FAILURES")

    (options, args) = parser.parse_args()
    N = int(options.number)
    t = int(options.failure)

    print options.version
    for i in range(10):
        inputs = [random.randint(0, 1) for _ in range(N)]
        #inputs = [1,0,0,1]
        print "Inputs:", inputs
        initiateThresholdSig(open(options.threshold_keys, 'r').read())
        initializeGIPC(PK=getKeys()[0])
        time1 = time.time()
        random_delay_binary_consensus(N, t, inputs, int(options.version))
        print "done", time.time()-time1
