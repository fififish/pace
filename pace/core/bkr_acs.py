from gevent import monkey
monkey.patch_all()

from broadcasts import initBeforeBinaryConsensus, cobalt_binary_consensus, binary_consensus, pace_binary_consensus, pace_biased_binary_consensus, pace_biased_binary_consensus_trigger, pace_crain_high_threshold_consensus, pace_crain_low_threshold_consensus, pace_biased_crain_high_threshold_consensus, pace_biased_crain_low_threshold_consensus
from utils import myRandom as random
from gevent import Greenlet
import gevent
from gevent.queue import Queue
# Run the BV_broadcast protocol with no corruptions and uniform random message delays
from utils import MonitoredInt, ACSException, greenletPacker

lockBA = Queue(1)
defaultBA = []
lockBA.put(1)


def acs(pid, N, t, version, Q, broadcast, receive):
    assert(isinstance(Q, list))
    assert(len(Q) == N)
    decideChannel = [Queue(1) for _ in range(N)]
    receivedChannelsFlags = []

    BA = [0]*N
    locker = Queue(1)
    locker2 = Queue(1)
    callbackCounter = [0]
    

    def callbackFactory(i):
        def _callback(val): # Get notified for i
            # Greenlet(callBackWrap(binary_consensus, callbackFactory(i)), pid,
            #         N, t, 1, make_bc(i), reliableBroadcastReceiveQueue[i].get).start()
            if not i in receivedChannelsFlags:
                receivedChannelsFlags.append(i)
                # mylog('B[%d]binary consensus_%d_starts with 1 at %f' % (pid, i, time.time()), verboseLevel=-1)
                #if len(receivedChannelsFlags) >= N-t:
                if (version == 3 or version == 7 or version == 8) and len(receivedChannelsFlags) >= N-t:
                   locker2.put("Key")
                if version == 1:
                    greenletPacker(Greenlet(binary_consensus, i, pid,
                        N, t, 1, decideChannel[i], make_bc(i), reliableBroadcastReceiveQueue[i].get),
                            'acs.callbackFactory.binary_consensus', (pid, N, t, Q, broadcast, receive)).start()
                elif version == 2:
                    greenletPacker(Greenlet(pace_binary_consensus, i, pid,
                        N, t, 1, 2, decideChannel[i], make_bc(i), reliableBroadcastReceiveQueue[i].get),
                            'acs.callbackFactory.pace_binary_consensus', (pid, N, t, Q, broadcast, receive)).start()
                elif version == 3:
                    greenletPacker(Greenlet(pace_biased_binary_consensus, i, pid,
                        N, t, 1,2, decideChannel[i], make_bc(i), reliableBroadcastReceiveQueue[i].get),
                            'acs.callbackFactory.pace_biased_binary_consensus', (pid, N, t, Q, broadcast, receive)).start()
                elif version == 4:
                    greenletPacker(Greenlet(cobalt_binary_consensus, i, pid,
                        N, t, 1, decideChannel[i], make_bc(i), reliableBroadcastReceiveQueue[i].get),
                            'acs.callbackFactory.cobalt_binary_consensus', (pid, N, t, Q, broadcast, receive)).start()
                elif version == 5:
                    greenletPacker(Greenlet(pace_crain_high_threshold_consensus, i, pid,
                        N, t, 1, 2, decideChannel[i], make_bc(i), reliableBroadcastReceiveQueue[i].get),
                            'acs.callbackFactory.pace_crain_high_threshold_consensus', (pid, N, t, Q, broadcast, receive)).start()
                elif version == 6:
                    greenletPacker(Greenlet(pace_crain_low_threshold_consensus, i, pid,
                        N, t, 1, 2, decideChannel[i], make_bc(i), reliableBroadcastReceiveQueue[i].get),
                            'acs.callbackFactory.pace_crain_low_threshold_consensus', (pid, N, t, Q, broadcast, receive)).start()
                elif version == 7:
                    greenletPacker(Greenlet(pace_biased_crain_high_threshold_consensus, i, pid,
                        N, t, 1, 2, decideChannel[i], make_bc(i), reliableBroadcastReceiveQueue[i].get),
                            'acs.callbackFactory.pace_biased_crain_high_threshold_consensus', (pid, N, t, Q, broadcast, receive)).start()
                elif version == 8:
                    greenletPacker(Greenlet(pace_biased_crain_low_threshold_consensus, i, pid,
                        N, t, 1, 2, decideChannel[i], make_bc(i), reliableBroadcastReceiveQueue[i].get),
                            'acs.callbackFactory.pace_biased_crain_low_threshold_consensus', (pid, N, t, Q, broadcast, receive)).start()
        return _callback

    for i, q in enumerate(Q):
        assert(isinstance(q, MonitoredInt))
        q.registerSetCallBack(callbackFactory(i))

    def make_bc(i):
        def _bc(m):
            broadcast(
                (i, m)
            )
        return _bc

    reliableBroadcastReceiveQueue = [Queue() for x in range(N)]

    def _listener():
        while True:
            sender, (instance, m) = receive()
            reliableBroadcastReceiveQueue[instance].put(
                    (sender, m)
                )

    greenletPacker(Greenlet(_listener), 'acs._listener', (pid, N, t, Q, broadcast, receive)).start()

    

    def listenerFactory(i, channel):
        def _listener():
            BA[i] = channel.get()
            if version == 1 or version == 2 or version == 4 or version == 5 or version == 6:
                if callbackCounter[0] >= 2*t and (not locker2.full()):
                    locker2.put("Key")  # Now we've got 2t+1 1's
                    if pid==0:
                        print "         getBA[o]", callbackCounter[0]
                callbackCounter[0] += 1
                if callbackCounter[0] == N and (not locker.full()):  # if we have all of them responded
                        locker.put("Key")
            else:
                callbackCounter[0] += 1
                if callbackCounter[0] >= N-t and (not locker.full()):  # if we have all of them responded
                #if callbackCounter[0] == N and (not locker.full()):  # if we have all of them responded
                        locker.put("Key")
                        
        return _listener
    
    #if version == 1 or version == 2 or version == 4 or version == 5 or version == 6:
    for i in range(N):
        greenletPacker(Greenlet(listenerFactory(i, decideChannel[i])),
            'acs.listenerFactory(i, decideChannel[i])', (pid, N, t, Q, broadcast, receive)).start()
    #if version == 1 or version == 2 or version == 4 or version == 5 or version == 6:
    locker2.get()

    # Now we feed 0 to all the other binary consensus protocols
    for i in range(N):
        if not i in receivedChannelsFlags:
            receivedChannelsFlags.append(i)
            if pid == 0:
                print ("[%d] proposing 0"%i)
            if version == 1:
                greenletPacker(Greenlet(binary_consensus, i, pid, N, t, 0,
                        decideChannel[i], make_bc(i), reliableBroadcastReceiveQueue[i].get),
                            'acs.binary_consensus', (pid, N, t, Q, broadcast, receive)).start()
            elif version == 2:
                greenletPacker(Greenlet(pace_binary_consensus, i, pid, N, t, 0, 2, 
                        decideChannel[i], make_bc(i), reliableBroadcastReceiveQueue[i].get),
                            'acs.pace_binary_consensus', (pid, N, t, Q, broadcast, receive)).start()
            elif version == 3:
                greenletPacker(Greenlet(pace_biased_binary_consensus, i, pid, N, t, 0, 2,
                        decideChannel[i], make_bc(i), reliableBroadcastReceiveQueue[i].get),
                            'acs.pace_biased_binary_consensus', (pid, N, t, Q, broadcast, receive)).start()
            elif version == 4:
                greenletPacker(Greenlet(cobalt_binary_consensus, i, pid, N, t, 0,
                        decideChannel[i], make_bc(i), reliableBroadcastReceiveQueue[i].get),
                            'acs.cobalt_binary_consensus', (pid, N, t, Q, broadcast, receive)).start()
            elif version == 5:
                greenletPacker(Greenlet(pace_crain_high_threshold_consensus, i, pid, N, t, 0, 2, 
                        decideChannel[i], make_bc(i), reliableBroadcastReceiveQueue[i].get),
                            'acs.pace_crain_high_threshold_consensus', (pid, N, t, Q, broadcast, receive)).start()
            elif version == 6:
                greenletPacker(Greenlet(pace_crain_low_threshold_consensus, i, pid, N, t, 0, 2, 
                        decideChannel[i], make_bc(i), reliableBroadcastReceiveQueue[i].get),
                            'acs.pace_crain_low_threshold_consensus', (pid, N, t, Q, broadcast, receive)).start()
            elif version == 7:
                greenletPacker(Greenlet(pace_biased_crain_high_threshold_consensus, i, pid, N, t, 0, 2, 
                        decideChannel[i], make_bc(i), reliableBroadcastReceiveQueue[i].get),
                            'acs.pace_biased_crain_high_threshold_consensus', (pid, N, t, Q, broadcast, receive)).start()
            elif version == 8:
                greenletPacker(Greenlet(pace_biased_crain_low_threshold_consensus, i, pid, N, t, 0, 2, 
                        decideChannel[i], make_bc(i), reliableBroadcastReceiveQueue[i].get),
                            'acs.pace_biased_crain_low_threshold_consensus', (pid, N, t, Q, broadcast, receive)).start()
    

    '''if version == 3 or version == 7 or version == 8:
        for i in range(N):
            greenletPacker(Greenlet(listenerFactory(i, decideChannel[i])),
                'acs.listenerFactory(i, decideChannel[i])', (pid, N, t, Q, broadcast, receive)).start()
        locker2.get()'''
    

    locker.get()  # Now we can check'''
    #BA = checkBA(BA, N, t)
    return BA

def checkBA(BA, N, t):
    global defaultBA
    if sum(BA) < N-t:  # If acs failed, we use a pre-set default common subset
        raise ACSException
    return BA


def random_delay_acs(N, t, inputs):

    assert(isinstance(inputs, list))

    maxdelay = 0.01

    # Instantiate the "broadcast" instruction
    def makeBroadcast(i):
        def _broadcast(v):
           def _deliver(j):
               buffers[j].put((i,v))

           for j in range(N):
               greenletPacker(Greenlet(_deliver, j),
                   'random_delay_acs._deliver', (N, t, inputs)).start_later(random.random()*maxdelay)

        return _broadcast

    def modifyMonitoredInt(monitoredInt):
        monitoredInt.data = 1

    while True:
        initBeforeBinaryConsensus()
        buffers = map(lambda _: Queue(1), range(N))
        ts = []
        for i in range(N):
            bc = makeBroadcast(i)
            recv = buffers[i].get
            input_clone = [MonitoredInt() for _ in range(N)]
            for j in range(N):
                greenletPacker(Greenlet(modifyMonitoredInt, input_clone[j]),
                    'random_delay_acs.modifyMonitoredInt', (N, t, inputs)).start_later(maxdelay * random.random())
            th = greenletPacker(Greenlet(acs, i, N, t, input_clone, bc, recv), 'random_delay_acs.acs', (N, t, inputs))
            th.start() # start_later(random.random() * maxdelay) is not necessary here
            ts.append(th)

        #if True:
        try:
            gevent.joinall(ts)
            break
        except gevent.hub.LoopExit: # Manual fix for early stop
            print "End"

if __name__=='__main__':
    #initTor()
    print "[ =========== ]"
    print "Testing binary consensus..."
    print "Testing ACS with different inputs..."
    Q = [1]*(2*1+1+1)+[0]*1
    random.shuffle(Q)
    random_delay_acs(5, 1, Q)

