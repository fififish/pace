# coding=utf-8
from gevent import Greenlet
from gevent.queue import Queue
from collections import defaultdict
from utils import dummyCoin, greenletPacker, getKeys
from ..commoncoin.thresprf_gipc import serialize, serialize1, deserialize, combine_and_verify


verbose = 0
from utils import makeCallOnce, \
    makeBroadcastWithTag, makeBroadcastWithTagAndRound, garbageCleaner, loopWrapper

FAILURE = 0 # FAILURE=0: no failure; FAILURE=1: flipped value; FAILURE=2: propose 0. The first f replicas are faulty if FAILURE= 1 or 2 
NumFaulty = 1 

# Input: a binary value
# Output: outputs one binary value, and thereafter possibly a second
# - If at least (t+1) of the honest parties input v, then v will be output by all honest parties
# (Note: it requires up to 2*t honest parties to deliver their messages. At the highest tolerance setting, this means *all* the honest parties)
# - If any honest party outputs a value, then it must have been input by some honest party. If only corrupted parties propose a value, it will never be output. 
def bv_broadcast(pid, N, t, broadcast, receive, output, release=lambda: None):
    '''
    The BV_Broadcast algorithm [MMR13]
    :param pid: my id number
    :param N: the number of parties
    :param t: the number of byzantine parties
    :param broadcast: broadcast channel
    :param receive: receive channel
    :param output: output channel
    :return: None
    '''
    assert N > 3 * t

    def input(my_v):
        # my_v : input valuef

        # My initial input value is v in (0,1)
        # assert my_v in (0, 1)

        # We'll output each of (0,1) at most once
        out = (makeCallOnce(lambda: output(0)),
               makeCallOnce(lambda: output(1)))

        # We'll relay each of (0,1) at most once
        received = defaultdict(set)

        def _bc(v):
            broadcast(v)

        relay = (makeCallOnce(lambda: _bc(0)),
                 makeCallOnce(lambda: _bc(1)))

        # Start by relaying my value
        relay[my_v]()
        outputed = []
        while True:
            (sender, v) = receive()

            assert v in (0, 1)
            assert sender in range(N)
            received[v].add(sender)
            # Relay after reaching first threshold
            if len(received[v]) >= t + 1:
                relay[v]()

            # Output after reaching second threshold
            if len(received[v]) >= 2 * t + 1:
                out[v]()
                if not v in outputed:
                    outputed.append(v)
                if len(outputed) == 2:
                    release()  # Release Channel
                    return  # We don't have to wait more

    return input

def pace_bv_broadcast(version, pid, N, t, round, broadcast, receive, output, release=lambda: None):
    '''
    The broadcast algorithm adapted for pace and ace
    :param pid: my id number
    :param N: the number of parties
    :param t: the number of byzantine parties
    :param broadcast: broadcast channel
    :param receive: receive channel
    :param output: output channel
    :return: None
    '''

    assert N > 3 * t


    def input(my_v,my_m,sval,delta=0):
        # my_v : input value
        #print "my_v", my_v, "my_m", my_m
        
        # My initial input value is v in (0,1)
        # assert my_v in (0, 1)

        # We'll output each of (0,1) at most once
        out = (makeCallOnce(lambda: output((0,delta))),
               makeCallOnce(lambda: output((1,delta))))

        # We'll relay each of (0,1) at most once
        received = defaultdict(set)

        def _bc(v,maj):
            broadcast((v,maj))

        relay = (makeCallOnce(lambda: _bc(0,my_m)),
                 makeCallOnce(lambda: _bc(1,my_m)))

        # Start by relaying my value
        relay[my_v]()
        outputed = []
        record = {}
        pval = {} # We need to check the V1 vals for 0 and 1. For simplicty, we use a map ot denote the values
        for i in range(3):
            pval[i] = 0 
        
        while True:
            (sender, (v,maj)) = receive()
            try:
                sender_record = record[sender]
                assert sender_record == maj
            except:
                record[sender] = maj

            assert v in (0, 1)
            assert sender in range(N)
            received[v].add(sender)
            pval[maj] = 1

            # Relay after reaching first threshold
            if len(received[v]) >= t + 1:
                relay[v]()
                if version== 2 and round == 1 and v == 1: #only for biased ba
                    delta = 1
                    global readytodecide 
                    readytodecide = True
                    out[v]()
                    if not v in outputed:
                        outputed.append(v)
                    if len(outputed) == 2:
                        release()  # Release Channel
                        return  # We don't have to wait any more

            # Output after reaching second threshold
            if len(received[v]) >= 2 * t + 1:
                if round == 1 or (round>1 and ((v!=sval and pval[v]==1 and pval[sval]==0 and pval[2]==0) or (v==sval and pval[1-v]==0))):
                    delta = 1

                out[v]()
                if not v in outputed:
                    outputed.append(v)
                if len(outputed) == 2:
                    release()  # Release Channel
                    return  # We don't have to wait more

    return input

def s_broadcast(version, pid, N, t, round, supportcoin, broadcast, receive, output, release=lambda: None):
    '''
    The s_broadcast algorithm of crain's broadcast
    :param pid: my id number
    :param N: the number of parties
    :param t: the number of byzantine parties
    :param broadcast: broadcast channel
    :param receive: receive channel
    :param output: output channel
    :return: None
    '''

    assert N > 3 * t
    
    # We'll relay each of (0,1) at most once
    #received = defaultdict(set)

    def input(my_v):
        # my_v : input valuef

        # My initial input value is v in (0,1)
        # assert my_v in (0, 1)

        # We'll output each of (0,1) at most once
        out = (makeCallOnce(lambda: output(0)),
               makeCallOnce(lambda: output(1)),
               makeCallOnce(lambda: output(2)))

        received = defaultdict(set)

        def _bc(v):
            broadcast(v)


        relay = (makeCallOnce(lambda: _bc(0)),
                 makeCallOnce(lambda: _bc(1)),
                 makeCallOnce(lambda: _bc(2)))

        # Start by relaying my value
        #if not supportcoin:
        relay[my_v]()

        outputed = []
        while True:
            (sender, v) = receive()

            assert v in (0, 1, 2)
            assert sender in range(N)
            received[v].add(sender)
            # Relay after reaching first threshold
            if len(received[v]) >= t + 1:
                relay[v]()

            # Output after reaching second threshold
            if len(received[v]) >= 2 * t + 1:
                out[v]()
                if not v in outputed:
                    outputed.append(v)
                if len(outputed) == 2:
                    release()  # Release Channel
                    return  # We don't have to wait more

    return input



class CommonCoinFailureException(Exception):
    pass

def shared_coin(instance, pid, N, t, broadcast, receive):
    '''
    A dummy version of the Shared Coin
    :param pid: my id number
    :param N: the number of parties
    :param t: the number of byzantine parties
    :param broadcast: broadcast channel
    :param receive: receive channel
    :return: yield values b
    '''
    received = defaultdict(set)
    outputQueue = defaultdict(lambda: Queue(1))
    PK, SKs, gg = getKeys()
    def _recv():
        while True:
            # New shares for some round r
            try:
                (i, (r, sig,proof_c,proof_z)) = receive()
            except:
                (i, (r, (sig,proof_c,proof_z))) = receive()
            assert i in range(N)
            assert r >= 0
            received[r].add((i, serialize1(sig),serialize1(proof_c),serialize1(proof_z)))

            # After reaching the threshold, compute the output and
            # make it available locally
            if len(received[r]) == t + 1:
                    h = PK.hash_message(str((r, instance)))
                    
                    def tmpFunc(r, t):
                        prfcoin = combine_and_verify(h, dict(tuple((t, deserialize(sig)) for t, sig, proof_c, proof_z in received[r])[:t+1]), dict(tuple((t, deserialize(proof_c)) for t, sig, proof_c, proof_z in received[r])[:t+1]), dict(tuple((t, deserialize(proof_z)) for t, sig, proof_c, proof_z in received[r])[:t+1]),gg)
                        #print ord(prfcoin[10])
                        #print prfcoin
                        outputQueue[r].put(ord(prfcoin[10]) & 1)  # explicitly convert to int
                    Greenlet(
                        tmpFunc, r, t
                    ).start()

    greenletPacker(Greenlet(_recv), 'shared_coin_dummy', (pid, N, t, broadcast, receive)).start()

    def getCoin(round):
        broadcast((round, SKs[pid].sign(PK.hash_message(str((round,instance))),gg)))  # I have to do mapping to 1..l
        return outputQueue[round].get()

    return getCoin


def high_shared_coin(instance, pid, N, t, broadcast, receive):
    '''
    high threshold comomn coin
    :param pid: my id number
    :param N: the number of parties
    :param t: the number of byzantine parties
    :param broadcast: broadcast channel
    :param receive: receive channel
    :return: yield values b
    '''
    received = defaultdict(set)
    outputQueue = defaultdict(lambda: Queue(1))
    PK, SKs, gg = getKeys()
    def _recv():
        while True:
            # New shares for some round r
            try:
                (i, (r, sig,proof_c,proof_z)) = receive()
            except:
                (i, (r, (sig,proof_c,proof_z))) = receive()
            assert i in range(N)
            assert r >= 0
            received[r].add((i, serialize1(sig),serialize1(proof_c),serialize1(proof_z)))

            # After reaching the threshold, compute the output and
            # make it available locally
            if len(received[r]) == 2*t + 1:
                    h = PK.hash_message(str((r, instance)))
                    
                    def tmpFunc(r, t):
                        prfcoin = combine_and_verify(h, dict(tuple((t, deserialize(sig)) for t, sig, proof_c, proof_z in received[r])[:2*t+1]), dict(tuple((t, deserialize(proof_c)) for t, sig, proof_c, proof_z in received[r])[:2*t+1]), dict(tuple((t, deserialize(proof_z)) for t, sig, proof_c, proof_z in received[r])[:2*t+1]),gg)
                        #print ord(prfcoin[10])
                        #print prfcoin
                        outputQueue[r].put(ord(prfcoin[10]) & 1)  # explicitly convert to int
                    Greenlet(
                        tmpFunc, r, t
                    ).start()

    greenletPacker(Greenlet(_recv), 'high_shared_coin_dummy', (pid, N, t, broadcast, receive)).start()

    def getCoin(round):
        broadcast((round, SKs[pid].sign(PK.hash_message(str((round,instance))),gg)))  # I have to do mapping to 1..l
        return outputQueue[round].get()

    return getCoin


def arbitary_adversary(pid, N, t, vi, broadcast, receive):
    pass  # TODO: implement our arbitrary adversaries

globalState = defaultdict(str)  # Just for debugging
decision = defaultdict(bool)
currentrounds = defaultdict(int)

def initBeforeBinaryConsensus(): # A dummy function now
    '''
    Initialize all the variables used by binary consensus.
    Actually these variables should be described as local variables.
    :return: None
    '''
    pass


def mv84consensus(pid, N, t, vi, broadcast, receive):
    '''
    Implementation of the multivalue consensus of [TURPIN, COAN, 1984]
    This will achieve a consensus among all the inputs provided by honest parties,
    or raise an alert if failed to achieve one.
    :param pid: my id number
    :param N: the number of parties
    :param t: the number of byzantine parties
    :param vi: input value, an integer
    :param broadcast: broadcast channel
    :param receive: receive channel
    :return: decided value or 0 (default value if failed to reach a consensus)
    '''
    # initialize v and p (same meaning as in the paper)
    mv84v = defaultdict(lambda: 'Empty')
    mv84p = defaultdict(lambda: False)
    # Initialize the locks and local variables
    mv84WaiterLock = Queue()
    mv84WaiterLock2 = Queue()
    mv84ReceiveDiff = set()
    mv84GetPerplex = set()
    reliableBroadcastReceiveQueue = Queue()

    def _listener():  # Hard-working Router for this layer
        while True:
            sender, (tag, m) = receive()
            if tag == 'V':
                mv84v[sender] = m
                if m != vi:
                    mv84ReceiveDiff.add(sender)
                    if len(mv84ReceiveDiff) >= (N - t) / 2.0:
                        mv84WaiterLock.put(True)
                # Fast-Stop: We don't need to wait for the rest (possibly)
                # malicious parties.
                if len(mv84v.keys()) >= N - t:
                    mv84WaiterLock.put(False)
            elif tag == 'B':
                mv84p[sender] = m
                if m:
                    mv84GetPerplex.add(sender)
                    if len(mv84GetPerplex) >= N - 2 * t:
                        mv84WaiterLock2.put(True)
                # Fast-Stop: We don't need to wait for the rest (possibly)
                # malicious parties.
                if len(mv84p.keys()) >= N - t:
                    mv84WaiterLock2.put(False)
            else:  # Re-route the msg to inner layer
                reliableBroadcastReceiveQueue.put(
                    (sender, (tag, m))
                )

    greenletPacker(Greenlet(_listener), 'mv84consensus._listener', (pid, N, t, vi, broadcast, receive)).start()

    makeBroadcastWithTag('V', broadcast)(vi)
    perplexed = mv84WaiterLock.get()  # See if I am perplexed

    makeBroadcastWithTag('B', broadcast)(perplexed)
    alert = mv84WaiterLock2.get() and 1 or 0  # See if we should alert


    decideChannel = Queue(1)
    greenletPacker(Greenlet(binary_consensus, pid, N, t, alert, decideChannel, broadcast, reliableBroadcastReceiveQueue.get),
        'mv84consensus.binary_consensus', (pid, N, t, vi, broadcast, receive)).start()
    agreedAlert = decideChannel.get()

    if agreedAlert:
        return 0  # some pre-defined default consensus value
    else:
        return vi


def checkFinishedWithGlobalState(N):
    '''
    Check if binary consensus is finished
    :param N: the number of parties
    :return: True if not finished, False if finished
    '''
    if len(globalState.keys()) < N:
        return True
    for i in globalState:
        if not globalState[i]:
            return True
    return False


def binary_consensus(instance, pid, N, t, vi, decide, broadcast, receive):
    '''
    Binary consensus from [MMR 13]. It takes an input vi and will finally write the decided value into _decide_ channel.
    :param pid: my id number
    :param N: the number of parties
    :param t: the number of byzantine parties
    :param vi: input value, an integer
    :param decide: deciding channel
    :param broadcast: broadcast channel
    :param receive: receive channel
    :return:
    '''

    # Messages received are routed to either a shared coin, the broadcast, or AUX
    coinQ = Queue(1)
    bcQ = defaultdict(lambda: Queue(1))
    auxQ = defaultdict(lambda: Queue(1))

    def _recv():
        while True:  #not finished[pid]:
            (i, (tag, m)) = receive()
            if tag == 'B':
                # Broadcast message
                r, msg = m
                greenletPacker(Greenlet(bcQ[r].put, (i, msg)),
                    'binary_consensus.bcQ[%d].put' % r, (pid, N, t, vi, decide, broadcast, receive)).start() # In case they block the router
            elif tag == 'C':
                # A share of a coin
                greenletPacker(Greenlet(coinQ.put, (i, m)),
                    'binary_consensus.coinQ.put', (pid, N, t, vi, decide, broadcast, receive)).start()
            elif tag == 'A':
                # Aux message
                r, msg = m
                greenletPacker(Greenlet(auxQ[r].put, (i, msg)),
                      'binary_consensus.auxQ[%d].put' % r, (pid, N, t, vi, decide, broadcast, receive)).start()
                pass
            

    greenletPacker(Greenlet(_recv), 'binary_consensus._recv', (pid, N, t, vi, decide, broadcast, receive)).start()

    def brcast_get(r):
        def _recv(*args, **kargs):
            return bcQ[r].get(*args, **kargs)

        return _recv

    received = [defaultdict(set), defaultdict(set)]

    coin = shared_coin(instance, pid, N, t, makeBroadcastWithTag('C', broadcast), coinQ.get)
    #print coin(1)

    def getWithProcessing(r, binValues, callBackWaiter):
        def _recv(*args, **kargs):
            sender, v = auxQ[r].get(*args, **kargs)
            assert v in (0, 1)
            assert sender in range(N)
            received[v][r].add(sender)
            # Check if conditions are satisfied
            threshold = N - t  # 2*t + 1 # N - t
            if True: #not finished[pid]:
                if len(binValues) == 1:
                    
                    if len(received[binValues[0]][r]) >= threshold and not callBackWaiter[r].full():
                        # Check passed
                        callBackWaiter[r].put(binValues)
                elif len(binValues) == 2:
    
                    if len(received[0][r].union(received[1][r])) >= threshold and not callBackWaiter[r].full():
                        callBackWaiter[r].put(binValues)
                    elif len(received[0][r]) >= threshold and not callBackWaiter[r].full():
                        callBackWaiter[r].put([0])
                    elif len(received[1][r]) >= threshold and not callBackWaiter[r].full():
                        callBackWaiter[r].put([1])
            return sender, v

        return _recv

    round = 0
    est = vi
    decided = False
    decidedNum = 0

    callBackWaiter = defaultdict(lambda: Queue(1))

    while True: # checkFinishedWithGlobalState(N): <- for distributed experiment we don't need this
        round += 1
        currentrounds[pid] = round
        #print "round %d"%round
        # Broadcast EST
        # TODO: let bv_broadcast receive
        bvOutputHolder = Queue(2)  # 2 possible values
        binValues = []

        def bvOutput(m):
            if not m in binValues:
                binValues.append(m)
                bvOutputHolder.put(m)

        def getRelease(channel):
            def _release():
                greenletPacker(Greenlet(garbageCleaner, channel),
                    'binary_consensus.garbageCleaner', (pid, N, t, vi, decide, broadcast, receive)).start()
            return _release

        br1 = greenletPacker(Greenlet(
            bv_broadcast(
                pid, N, t, makeBroadcastWithTagAndRound('B', broadcast, round),
                brcast_get(round), bvOutput, getRelease(bcQ[round])),
            est), 'binary_consensus.bv_broadcast(%d, %d, %d)' % (pid, N, t), (pid, N, t, vi, decide, broadcast, receive))
        br1.start()
        w = bvOutputHolder.get()  # Wait until output is not empty

        broadcast(('A', (round, w)))
        greenletPacker(Greenlet(loopWrapper(getWithProcessing(round, binValues, callBackWaiter))),
            'binary_consensus.loopWrapper(getWithProcessing(round, binValues, callBackWaiter))',
                    (pid, N, t, vi, decide, broadcast, receive)).start()

        values = callBackWaiter[round].get()  # wait until the conditions are satisfied
        s = coin(round)
        # Here corresponds to a proof that if one party decides at round r,
        # then in all the following rounds, everybody will propose r as an estimation. (Lemma 2, Lemma 1)
        # An abandoned party is a party who has decided but no enough peers to help him end the loop.
        # Lemma: # of abandoned party <= t
        if decided and decidedNum == s:  # infinite-message fix
            break
        if len(values) == 1:
            if values[0] == s:
                # decide s
                if not decided:
                    globalState[pid] = "%d" % s
                    decide.put(s)
                    decided = True
                    decidedNum = s
                    if pid==0:
                        print "[PID: %d] Decided on value: %d, round: %d" %(pid,s,round)

            else:
                pass
            est = values[0]
        else:
            est = s



def cobalt_binary_consensus(instance, pid, N, t, vi, decide, broadcast, receive):
    '''
    Binary consensus from [MMR 13]. It takes an input vi and will finally write the decided value into _decide_ channel.
    :param pid: my id number
    :param N: the number of parties
    :param t: the number of byzantine parties
    :param vi: input value, an integer
    :param decide: deciding channel
    :param broadcast: broadcast channel
    :param receive: receive channel
    :return:
    '''

    # Messages received are routed to either a shared coin, the broadcast, or AUX
    coinQ = Queue(1)
    bcQ = defaultdict(lambda: Queue(1))
    auxQ = defaultdict(lambda: Queue(1))
    confQ = defaultdict(lambda: Queue(1))

    if FAILURE == 1 and pid >= 0 and pid < NumFaulty:
        vi = 1 - vi 
    elif FAILURE == 2 and pid >= 0 and pid < NumFaulty:
        vi = 0 

    def _recv():
        while True:  #not finished[pid]:
            (i, (tag, m)) = receive()
            if tag == 'B':
                # Broadcast message
                r, msg = m
                greenletPacker(Greenlet(bcQ[r].put, (i, msg)),
                    'cobalt_binary_consensus.bcQ[%d].put' % r, (pid, N, t, vi, decide, broadcast, receive)).start() # In case they block the router
            elif tag == 'C':
                # A share of a coin
                greenletPacker(Greenlet(coinQ.put, (i, m)),
                    'cobalt_binary_consensus.coinQ.put', (pid, N, t, vi, decide, broadcast, receive)).start()
            elif tag == 'A':
                # Aux message
                r, msg = m
                greenletPacker(Greenlet(auxQ[r].put, (i, msg)),
                      'cobalt_binary_consensus.auxQ[%d].put' % r, (pid, N, t, vi, decide, broadcast, receive)).start()
                pass
            elif tag == 'F':
                # Aux message
                r, msg = m
                greenletPacker(Greenlet(confQ[r].put, (i, msg)),
                      'cobalt_binary_consensus.confQ[%d].put' % r, (pid, N, t, vi, decide, broadcast, receive)).start()
                pass

    greenletPacker(Greenlet(_recv), 'cobalt_binary_consensus._recv', (pid, N, t, vi, decide, broadcast, receive)).start()

    def brcast_get(r):
        def _recv(*args, **kargs):
            return bcQ[r].get(*args, **kargs)

        return _recv

    received = [defaultdict(set), defaultdict(set)]
    conf_values = defaultdict(lambda: {(0,): set(), (1,): set(), (0, 1): set()})

    coin = shared_coin(instance, pid, N, t, makeBroadcastWithTag('C', broadcast), coinQ.get)
    #print coin(1)

    def getWithProcessing(r, binValues, callBackWaiter):
        def _recv(*args, **kargs):
            sender, v = auxQ[r].get(*args, **kargs)
            assert v in (0, 1)
            assert sender in range(N)
            received[v][r].add(sender)
            # Check if conditions are satisfied
            threshold = N - t  # 2*t + 1 # N - t
            if True: #not finished[pid]:
                if len(binValues) == 1:
                    if len(received[binValues[0]][r]) >= threshold and not callBackWaiter[r].full():
                        # Check passed
                        callBackWaiter[r].put(binValues)
                elif len(binValues) == 2:
    
                    if len(received[0][r].union(received[1][r])) >= threshold and not callBackWaiter[r].full():
                        callBackWaiter[r].put(binValues)
                    elif len(received[0][r]) >= threshold and not callBackWaiter[r].full():
                        callBackWaiter[r].put([0])
                    elif len(received[1][r]) >= threshold and not callBackWaiter[r].full():
                        callBackWaiter[r].put([1])
            return sender, v

        return _recv

    def finalProcessing(r, binValues, finalWaiter):
        def _recv(*args, **kargs):
            sender, val = confQ[r].get(*args, **kargs)
            v= tuple()
            if 0 in val:
                v+=(0,)
            if 1 in val:
                v+=(1,)
        
            assert v in ((0,), (1,),(0,1))
            assert sender in range(N)
            #try:
            conf_values[r][v].add(sender)
            #except:
            #    print "what?"
            # Check if conditions are satisfied
            threshold = N - t  # 2*t + 1 # N - t
            #print "conf", conf_values
            if True: #not finished[pid]:
                
                if len(binValues) == 1:
                    if len(conf_values[r][(binValues[0],)]) >= threshold and not finalWaiter[r].full():
                        # Check passed
                        finalWaiter[r].put(binValues)
                elif len(binValues) == 2:
                    if len(conf_values[r][(0,)]) >= threshold and not finalWaiter[r].full():
                        finalWaiter[r].put([0])
                    elif len(conf_values[r][(1,)]) >= threshold and not finalWaiter[r].full():
                        finalWaiter[r].put([1])
                    elif (sum(len(senders) for conf_value, senders in
                                conf_values[r].items()) >= N - t):
                        finalWaiter[r].put(binValues)
            return sender, v

        return _recv

    round = 0
    est = vi
    decided = False
    decidedNum = 0

    callBackWaiter = defaultdict(lambda: Queue(1))
    finalWaiter = defaultdict(lambda: Queue(1))

    while True: # checkFinishedWithGlobalState(N): <- for distributed experiment we don't need this
        round += 1
        currentrounds[pid] = round
        #print "round %d"%round
        # Broadcast EST
        # TODO: let bv_broadcast receive
        bvOutputHolder = Queue(2)  # 2 possible values
        binValues = []

        if FAILURE == 1 and pid >= 0 and pid < NumFaulty:
            est = 1 - est 
        elif FAILURE == 2 and pid >= 0 and pid < NumFaulty:
            est = 0 

        def bvOutput(m):
            if not m in binValues:
                binValues.append(m)
                bvOutputHolder.put(m)

        def getRelease(channel):
            def _release():
                greenletPacker(Greenlet(garbageCleaner, channel),
                    'cobalt_binary_consensus.garbageCleaner', (pid, N, t, vi, decide, broadcast, receive)).start()
            return _release

        br1 = greenletPacker(Greenlet(
            bv_broadcast(
                pid, N, t, makeBroadcastWithTagAndRound('B', broadcast, round),
                brcast_get(round), bvOutput, getRelease(bcQ[round])),
            est), 'cobalt_binary_consensus.bv_broadcast(%d, %d, %d)' % (pid, N, t), (pid, N, t, vi, decide, broadcast, receive))
        br1.start()
        w = bvOutputHolder.get()  # Wait until output is not empty

        if FAILURE == 1 and pid >= 0 and pid < NumFaulty:
            w = 1 - w 
        elif FAILURE == 2 and pid >= 0 and pid < NumFaulty:
            w = 0 

        broadcast(('A', (round, w)))
        greenletPacker(Greenlet(loopWrapper(getWithProcessing(round, binValues, callBackWaiter))),
            'cobalt_binary_consensus.loopWrapper(getWithProcessing(round, binValues, callBackWaiter))',
                    (pid, N, t, vi, decide, broadcast, receive)).start()

        values = callBackWaiter[round].get()  # wait until the conditions are satisfied

        broadcast(('F', (round, values)))

        greenletPacker(Greenlet(loopWrapper(finalProcessing(round, binValues, finalWaiter))),
            'cobalt_binary_consensus.loopWrapper(finalProcessing(round, binValues, finalWaiter))',
                    (pid, N, t, vi, decide, broadcast, receive)).start()

        values = finalWaiter[round].get()

        s = coin(round)
        # Here corresponds to a proof that if one party decides at round r,
        # then in all the following rounds, everybody will propose r as an estimation. (Lemma 2, Lemma 1)
        # An abandoned party is a party who has decided but no enough peers to help him end the loop.
        # Lemma: # of abandoned party <= t
        if decided and decidedNum == s:  # infinite-message fix
            break
        if len(values) == 1:
            if values[0] == s:
                # decide s
                if not decided:
                    globalState[pid] = "%d" % s
                    decide.put(s)
                    decided = True
                    decidedNum = s
                    #if pid==0:
                    #    print "[PID: %d] Cobalt decided on value: %d, round: %d" %(pid,s,round)

            else:
                pass
            est = values[0]
        else:
            est = s


def pace_binary_consensus(instance, pid, N, t, vi, mi, decide, broadcast, receive):
    '''
    PACE Pillar binary consensus: It takes an input vi and will finally write the decided value into _decide_ channel.
    :param pid: my id number
    :param N: the number of parties
    :param t: the number of byzantine parties
    :param vi: input value, an integer
    :param mi: carry over value, 0, 1, or 2 (\bot in the protocol)
    :param decide: deciding channel
    :param broadcast: broadcast channel
    :param receive: receive channel
    :return:
    '''

    # Messages received are routed to either a shared coin, the broadcast, or AUX
    coinQ = Queue(1)
    bcQ = defaultdict(lambda: Queue(1))
    auxQ = defaultdict(lambda: Queue(1))

    if FAILURE == 1 and pid >= 0 and pid < NumFaulty:
        vi = 1 - vi 
    elif FAILURE == 2 and pid >= 0 and pid < NumFaulty:
        vi = 0 

    def _recv():
        while True:  #not finished[pid]:
            (i, (tag, m)) = receive()
            if tag == 'D':
                # Broadcast message
                r, msg = m
                greenletPacker(Greenlet(bcQ[r].put, (i, msg)),
                    'pace_binary_consensus.bcQ[%d].put' % r, (pid, N, t, vi, mi, decide, broadcast, receive)).start() # In case they block the router
            elif tag == 'C':
                # A share of a coin
                greenletPacker(Greenlet(coinQ.put, (i, m)),
                    'pace_binary_consensus.coinQ.put', (pid, N, t, vi, mi, decide, broadcast, receive)).start()
            elif tag == 'E':
                # Aux message
                r, msg, maj = m
                greenletPacker(Greenlet(auxQ[r].put, (i, msg, maj)),
                      'pace_binary_consensus.auxQ[%d].put' % r, (pid, N, t, vi, mi, decide, broadcast, receive)).start()
                pass

    greenletPacker(Greenlet(_recv), 'pace_binary_consensus._recv', (pid, N, t, vi, mi, decide, broadcast, receive)).start()

    def brcast_get(r):
        def _recv(*args, **kargs):
            return bcQ[r].get(*args, **kargs)

        return _recv

    received = [defaultdict(set), defaultdict(set), defaultdict(set)]
    majs = [defaultdict(set), defaultdict(set), defaultdict(set)]

    coin = shared_coin(instance, pid, N, t, makeBroadcastWithTag('C', broadcast), coinQ.get)
    #print coin(1)

    def getWithProcessing(r, svalprime, delta, majority, readytodecide, binValues, callBackWaiter):
        def _recv(*args, **kargs):
            sender, v, maj = auxQ[r].get(*args, **kargs)
            assert v in (0, 1, 2) # 2 for \bot value
            assert maj in (0, 1, 2)
            assert sender in range(N)
            #if sender == 0:
            #    print ("[%d] received %d from node 0" %(pid,v))

            received[v][r].add(sender)
            majs[v][maj].add(sender)

            # Check if conditions are satisfied
            threshold = N - t  # 2*t + 1 # N - t
            
            
            global readytodecide

            if True: #not finished[pid]:
                
                if len(binValues) == 1:
                    if len(received[binValues[0]][r]) >= threshold and not callBackWaiter[r].full():
                        # Check passed
                        majority = binValues[0]
                        callBackWaiter[r].put(binValues)
                        readytodecide = True 
                elif round > 1 and (len(received[2][r]) >= threshold or len(received[0][r]) < threshold or len(received[1][r]) < threshold) and not callBackWaiter[r].full(): 
                    if len(received[0][r]) >= t+1:
                        majority = 0
                    elif len(received[1][r]) >= t+1:
                        majority = 1
                    else:
                        majority = 2
                    if len(majs[0][r]) >= threshold:
                        callBackWaiter[r].put([0])
                        if svalprime == 0:
                            readytodecide = True
                        return 
                    if len(majs[1][r]) >= threshold:
                        callBackWaiter[r].put([1])
                        if svalprime == 1:
                            readytodecide = True
                        return 
                    if len(majs[1][r].union(majs[0][r])) >= threshold:
                        tmp = []
                        tmp.append(svalprime)
                        callBackWaiter[r].put(tmp)
                        return 
                    callBackWaiter[r].put([0,1])
                elif len(binValues) == 2:
                    if len(received[0][r]) >= t+1:
                        majority = 0
                    elif len(received[1][r]) >= t+1:
                        majority = 1
                    else:
                        majority = 2
                    if len(received[0][r].union(received[1][r])) >= threshold and not callBackWaiter[r].full():
                        callBackWaiter[r].put(binValues)
                    elif len(received[0][r]) >= threshold and not callBackWaiter[r].full():
                        callBackWaiter[r].put([0])
                        readytodecide = True
                    elif len(received[1][r]) >= threshold and not callBackWaiter[r].full():
                        callBackWaiter[r].put([1])
                        readytodecide = True
                
            return sender, v

        return _recv

    round = 0
    est = vi
    maj = mi
    sval = 0
    decided = False
    decidedNum = 0
    global delta 
    delta = 0
    svalprime = 0        
        

    callBackWaiter = defaultdict(lambda: Queue(1))

    while True: # checkFinishedWithGlobalState(N): <- for distributed experiment we don't need this
        round += 1
        
        #print "PID %d, round %d"%(pid,round)
        # Broadcast EST
        # TODO: let bv_broadcast receive
        bvOutputHolder = Queue(2)  # 2 possible values
        binValues = []
        global majority 
        majority = 2
        global readytodecide 
        readytodecide = False 

        if FAILURE == 1 and pid >= 0 and pid < NumFaulty:
            est = 1 - est 
        elif FAILURE == 2 and pid >= 0 and pid < NumFaulty:
            est = 0 

        def bvOutput(msg):
            m,d = msg
            global delta
            delta = d
            
            if not m in binValues:
                binValues.append(m)
                bvOutputHolder.put(m)

        def getRelease(channel):
            def _release():
                greenletPacker(Greenlet(garbageCleaner, channel),
                    'pace_binary_consensus.garbageCleaner', (pid, N, t, vi, decide, broadcast, receive)).start()
            return _release

        br1 = greenletPacker(Greenlet(
            pace_bv_broadcast(
                1,pid, N, t, round,  makeBroadcastWithTagAndRound('D', broadcast, round),
                brcast_get(round), bvOutput, getRelease(bcQ[round])),
            est,maj,sval), 'pace_binary_consensus.pace_bv_broadcast(%d, %d, %d)' % (pid, N, t), (pid, N, t, round, vi, mi, decide, broadcast, receive))
        br1.start()
        w = bvOutputHolder.get()  # Wait until output is not empty

        if FAILURE == 1 and pid >= 0 and pid < NumFaulty:
            w = 1 - w 
        elif FAILURE == 2 and pid >= 0 and pid < NumFaulty:
            w = 0 

        if delta == 1:
            broadcast(('E', (round, w, w)))
        else:
            #print "**pid %s: round %s sending aux(2)"%( pid, round)
            broadcast(('E', (round, 2, w)))

        
        #readytodecide = False
        greenletPacker(Greenlet(loopWrapper(getWithProcessing(round, svalprime, delta, majority, readytodecide, binValues, callBackWaiter))),
            'pace_binary_consensus.loopWrapper(getWithProcessing(round, svalprime, binValues, callBackWaiter))',
                    (pid, N, t, vi, decide, broadcast, receive)).start()

        values = callBackWaiter[round].get()  # wait until the conditions are satisfied

        s = coin(round)
        # Here corresponds to a proof that if one party decides at round r,
        # then in all the following rounds, everybody will propose r as an estimation. (Lemma 2, Lemma 1)
        # An abandoned party is a party who has decided but no enough peers to help him end the loop.
        # Lemma: # of abandoned party <= t
        if decided and decidedNum == s:  # infinite-message fix
            break
        
        
        svalprime = s 
        
        if len(values)==1:
            if values[0] == s and readytodecide == True:
                # decide s
                if not decided:
                    globalState[pid] = "%d" % s
                    decide.put(s)
                    decided = True
                    decidedNum = s
                    if pid == 0:
                        print "[PID: %d] Protocol ends with value: %d, round: %d" %(pid,s,round)

            else:
                pass
               
            est = values[0]
            maj = est
        else:
            est = s
            if round == 1:
                maj = majority 
            else:
                maj = 0 # in the paper majority is set to majority(vals), we just set it to 0 while safety should not be violated
        
        sval = s



def pace_crain_high_threshold_consensus(instance, pid, N, t, vi, mi, decide, broadcast, receive):
    '''
    Crain's binary consensus with high threshold common coins: It takes an input vi and will finally write the decided value into _decide_ channel.
    :param pid: my id number
    :param N: the number of parties
    :param t: the number of byzantine parties
    :param vi: input value, an integer
    :param mi: carry over value, 0, 1, or 2 (\bot in the protocol)
    :param decide: deciding channel
    :param broadcast: broadcast channel
    :param receive: receive channel
    :return:
    '''
    
    # Messages received are routed to either a shared coin, the broadcast, or AUX
    coinQ = Queue(1)
    bcQ = defaultdict(lambda: Queue(1))
    auxQ = defaultdict(lambda: Queue(1))
    global supportcoin 
    supportcoin = False

    if FAILURE == 1 and pid >= 0 and pid < NumFaulty:
        vi = 1 - vi 
    elif FAILURE == 2 and pid >= 0 and pid < NumFaulty:
        vi = 0 

    def _recv():
        while True:  #not finished[pid]:
            (i, (tag, m)) = receive()
            if tag == 'B':
                # Broadcast message
                r, msg = m
                greenletPacker(Greenlet(bcQ[r].put, (i, msg)),
                    'pace_crain_high_threshold_consensus.bcQ[%d].put' % r, (pid, N, t, vi, mi, decide, broadcast, receive)).start() 
            elif tag == 'C':
                # A share of a coin
                greenletPacker(Greenlet(coinQ.put, (i, m)),
                    'pace_crain_high_threshold_consensus.coinQ.put', (pid, N, t, vi, mi, decide, broadcast, receive)).start()
            elif tag == 'A':
                # Aux message
                r, msg = m
                greenletPacker(Greenlet(auxQ[r].put, (i, msg)),
                      'pace_crain_high_threshold_consensus.auxQ[%d].put' % r, (pid, N, t, vi, mi, decide, broadcast, receive)).start()
                pass


    greenletPacker(Greenlet(_recv), 'pace_crain_high_threshold_consensus._recv', (pid, N, t, vi, mi, decide, broadcast, receive)).start()

    def brcast_get(r):
        def _recv(*args, **kargs):
            return bcQ[r].get(*args, **kargs)

        return _recv

    received = [defaultdict(set), defaultdict(set), defaultdict(set)]

    coin = high_shared_coin(instance, pid, N, t, makeBroadcastWithTag('C', broadcast), coinQ.get)
    #print coin(1)

    def getWithProcessing(r, binValues, callBackWaiter):
        def _recv(*args, **kargs):
            sender, v = auxQ[r].get(*args, **kargs)
            assert v in (0, 1) # 2 for \bot value
            assert sender in range(N)
            #if sender == 0:
            #    print ("[%d] received %d from node 0" %(pid,v))

            received[v][r].add(sender)

            # Check if conditions are satisfied
            threshold = N - t  # 2*t + 1 # N - t
            

            if True: 
                if len(binValues) == 1:
                    if len(received[binValues[0]][r]) >= threshold and not callBackWaiter[r].full():
                        # Check passed
                        callBackWaiter[r].put(binValues)
                elif len(binValues) == 2:
                    if len(received[0][r].union(received[1][r])) >= threshold and not callBackWaiter[r].full():
                        callBackWaiter[r].put(binValues)
                    elif len(received[0][r]) >= threshold and not callBackWaiter[r].full():
                        callBackWaiter[r].put([0])
                    elif len(received[1][r]) >= threshold and not callBackWaiter[r].full():
                        callBackWaiter[r].put([1])
                
            return sender, v

        return _recv

    round = 0
    est = vi
    decided = False
    decidedNum = 0      
        

    callBackWaiter = defaultdict(lambda: Queue(1))

    
    binValues = []
    bvOutputHolder = Queue(2)
    while True: # checkFinishedWithGlobalState(N): <- for distributed experiment we don't need this
        round += 1
        #bvOutputHolder = Queue(2)  # 2 possible values

        #print "PID %d, round %d"%(pid,round)
        # Broadcast EST
        # TODO: let bv_broadcast receive
        

        if FAILURE == 1 and pid >= 0 and pid < NumFaulty:
            est = 1 - est 
        elif FAILURE == 2 and pid >= 0 and pid < NumFaulty:
            est = 0 

        #if est in binValues:
        if 1-est in binValues and est in binValues:
            #binValues = [] 
            #binValues.append(est)
            bvOutputHolder = Queue(2)
            bvOutputHolder.put(est)
        elif est in binValues:
            bvOutputHolder = Queue(2)
            bvOutputHolder.put(est)
            
        

        def bvOutput(m):
            if not m in binValues:
                binValues.append(m)
                bvOutputHolder.put(m)
    
        '''if est in binValues:
            if 1-est in binValues:
                binValues = [] 
                binValues.append(1-est)
                bvOutputHolder.put(1-est)
            else:
                binValues = []'''
        
        def getRelease(channel):
            def _release():
                greenletPacker(Greenlet(garbageCleaner, channel),
                    'pace_crain_high_threshold_consensus.garbageCleaner', (pid, N, t, vi, decide, broadcast, receive)).start()
            return _release

        br1 = greenletPacker(Greenlet(
            s_broadcast(
                1,pid, N, t, round, supportcoin, makeBroadcastWithTagAndRound('B', broadcast, round),
                brcast_get(round), bvOutput, getRelease(bcQ[round])),
            est), 'pace_crain_high_threshold_consensus.s_broadcast(%d, %d, %d)' % (pid, N, t), (pid, N, t, round, vi, mi, decide, broadcast, receive))
        br1.start()

        w = bvOutputHolder.get()  # Wait until output is not empty

        if FAILURE == 1 and pid >= 0 and pid < NumFaulty:
            w = 1 - w 
        elif FAILURE == 2 and pid >= 0 and pid < NumFaulty:
            w = 0 

        
        broadcast(('A', (round, w)))
        
        
        greenletPacker(Greenlet(loopWrapper(getWithProcessing(round, binValues, callBackWaiter))),
            'pace_crain_high_threshold_consensus.loopWrapper(getWithProcessing(round, binValues, callBackWaiter))',
                    (pid, N, t, vi, decide, broadcast, receive)).start()

        values = callBackWaiter[round].get()  # wait until the conditions are satisfied
        


        s = coin(round)
        # Here corresponds to a proof that if one party decides at round r,
        # then in all the following rounds, everybody will propose r as an estimation. (Lemma 2, Lemma 1)
        # An abandoned party is a party who has decided but no enough peers to help him end the loop.
        # Lemma: # of abandoned party <= t
        if decided and decidedNum == s:  # infinite-message fix
            break
        
        #est = s
        if len(values)==1:
            if values[0] == s:
                # decide s
                if not decided:
                    globalState[pid] = "%d" % s
                    decide.put(s)
                    decided = True
                    decidedNum = s
                    if pid == 0:
                        print "[PID: %d] %d Protocol ends with value: %d, round: %d" %(instance,pid,s,round)
                supportcoin = True

            else:
                supportcoin = False
            est = values[0]
        else:
            supportcoin = True
            est = s
        

def pace_crain_low_threshold_consensus(instance, pid, N, t, vi, mi, decide, broadcast, receive):
    '''
    Crain's binary consensus with low threshold common coins: It takes an input vi and will finally write the decided value into _decide_ channel.
    Crain's protocol relies on weak coins. We use low threshold prf instead. 
    We also implement the fast path presented in ADKG paper
    :param pid: my id number
    :param N: the number of parties
    :param t: the number of byzantine parties
    :param vi: input value, an integer
    :param mi: carry over value, 0, 1, or 2 (\bot in the protocol)
    :param decide: deciding channel
    :param broadcast: broadcast channel
    :param receive: receive channel
    :return:
    '''
    
    # Messages received are routed to either a shared coin, the broadcast, or AUX
    coinQ = Queue(1)
    bcQ = defaultdict(lambda: Queue(1))
    auxQ = defaultdict(lambda: Queue(1))
    sbcQ = defaultdict(lambda: Queue(1))
    global supportcoin 
    supportcoin = False

    if FAILURE == 1 and pid >= 0 and pid < NumFaulty:
        vi = 1 - vi 
    elif FAILURE == 2 and pid >= 0 and pid < NumFaulty:
        vi = 0 

    def _recv():
        while True:  #not finished[pid]:
            (i, (tag, m)) = receive()
            if tag == 'B' :
                # Broadcast message
                r, msg = m
                greenletPacker(Greenlet(bcQ[r].put, (i, msg)),
                    'pace_crain_low_threshold_consensus.bcQ[%d].put' % r, (pid, N, t, vi, mi, decide, broadcast, receive)).start() 
            elif tag == 'G' :
                # Broadcast message
                r, msg = m
                greenletPacker(Greenlet(sbcQ[r].put, (i, msg)),
                    'pace_crain_low_threshold_consensus.bcQ[%d].put' % r, (pid, N, t, vi, mi, decide, broadcast, receive)).start() 
            elif tag == 'C':
                # A share of a coin
                greenletPacker(Greenlet(coinQ.put, (i, m)),
                    'pace_crain_low_threshold_consensus.coinQ.put', (pid, N, t, vi, mi, decide, broadcast, receive)).start()
            elif tag == 'A' or tag == 'H':
                # Aux message
                r, msg = m
                greenletPacker(Greenlet(auxQ[r].put, (i, msg)),
                      'pace_crain_low_threshold_consensus.auxQ[%d].put' % r, (pid, N, t, vi, mi, decide, broadcast, receive)).start()
                pass


    greenletPacker(Greenlet(_recv), 'pace_crain_low_threshold_consensus._recv', (pid, N, t, vi, mi, decide, broadcast, receive)).start()

    def brcast_get(r):
        def _recv(*args, **kargs):
            return bcQ[r].get(*args, **kargs)

        return _recv
    
    def second_brcast_get(r):
        def _recv(*args, **kargs):
            return sbcQ[r].get(*args, **kargs)

        return _recv

    received = [defaultdict(set), defaultdict(set), defaultdict(set)]

    coin = shared_coin(instance, pid, N, t, makeBroadcastWithTag('C', broadcast), coinQ.get)
    #print coin(1)

    def getWithProcessing(r, binValues, callBackWaiter):
        def _recv(*args, **kargs):
            sender, v = auxQ[r].get(*args, **kargs)
            assert v in (0, 1) # 2 for \bot value
            assert sender in range(N)
            #if sender == 0:
            #    print ("[%d] received %d from node 0" %(pid,v))

            received[v][r].add(sender)

            # Check if conditions are satisfied
            threshold = N - t  # 2*t + 1 # N - t
            

            if True: 
                if len(binValues) == 1:
                    if len(received[binValues[0]][r]) >= threshold and not callBackWaiter[r].full():
                        # Check passed
                        callBackWaiter[r].put(binValues)
                elif len(binValues) == 2:
                    if len(received[0][r].union(received[1][r])) >= threshold and not callBackWaiter[r].full():
                        callBackWaiter[r].put(binValues)
                    elif len(received[0][r]) >= threshold and not callBackWaiter[r].full():
                        callBackWaiter[r].put([0])
                    elif len(received[1][r]) >= threshold and not callBackWaiter[r].full():
                        callBackWaiter[r].put([1])
                
            return sender, v

        return _recv
    

    round = 0
    est = vi
    decided = False
    decidedNum = 0      
        

    callBackWaiter = defaultdict(lambda: Queue(1))

    
    while True: # checkFinishedWithGlobalState(N): <- for distributed experiment we don't need this
        round += 1
        
        #print "PID %d, round %d"%(pid,round)
        # Broadcast EST
        # TODO: let bv_broadcast receive
        bvOutputHolder = Queue(2)  # 2 possible values
        binValues = []

        if FAILURE == 1 and pid >= 0 and pid < NumFaulty:
            est = 1 - est 
        elif FAILURE == 2 and pid >= 0 and pid < NumFaulty:
            est = 0 


        def bvOutput(m):
            if not m in binValues:
                binValues.append(m)
                bvOutputHolder.put(m)


        def getRelease(channel):
            def _release():
                greenletPacker(Greenlet(garbageCleaner, channel),
                    'pace_crain_low_threshold_consensus.garbageCleaner', (pid, N, t, vi, decide, broadcast, receive)).start()
            return _release
        

        # we reuse the s_broadcast channel, and simply set supportcoin to false so that every node braodcasts its value
        br1 = greenletPacker(Greenlet(
            s_broadcast(
                1,pid, N, t, round, False, makeBroadcastWithTagAndRound('B', broadcast, round),
                brcast_get(round), bvOutput, getRelease(bcQ[round])),
            est), 'pace_crain_low_threshold_consensus.s_broadcast(%d, %d, %d)' % (pid, N, t), (pid, N, t, round, vi, mi, decide, broadcast, receive))
        br1.start()
        
        w = bvOutputHolder.get()  # Wait until output is not empty

        if FAILURE == 1 and pid >= 0 and pid < NumFaulty:
            w = 1 - w 
        elif FAILURE == 2 and pid >= 0 and pid < NumFaulty:
            w = 0 

        broadcast(('A', (round, w)))
        
        
        greenletPacker(Greenlet(loopWrapper(getWithProcessing(round, binValues, callBackWaiter))),
            'pace_crain_low_threshold_consensus.loopWrapper(getWithProcessing(round, binValues, callBackWaiter))',
                    (pid, N, t, vi, decide, broadcast, receive)).start()

        values = callBackWaiter[round].get()  # wait until the conditions are satisfied
        
        #now start the 2nd round of sbv_broadcast
        auxQ = defaultdict(lambda: Queue(1))
        secondbvOutputHolder = Queue(2)  # 2 possible values
        secondbinValues = []

        def secondbvOutput(m):
            if not m in secondbinValues:
                secondbinValues.append(m)
                secondbvOutputHolder.put(m)

        if len(values) == 1:
            w = values[0]
        else:
            w = 2
        
        br1 = greenletPacker(Greenlet(
            s_broadcast(
                1,pid, N, t, round, False, makeBroadcastWithTagAndRound('G', broadcast, round),
                second_brcast_get(round), secondbvOutput, getRelease(bcQ[round])),
            w), 'pace_crain_low_threshold_consensus.s_broadcast(%d, %d, %d)' % (pid, N, t), (pid, N, t, round, w, mi, decide, broadcast, receive))
        br1.start()
        
        w = secondbvOutputHolder.get()
        if FAILURE == 1 and pid >= 0 and pid < NumFaulty:
            w = 1 - w 
        elif FAILURE == 2 and pid >= 0 and pid < NumFaulty:
            w = 0 

        secondcallBackWaiter = defaultdict(lambda: Queue(1))
        broadcast(('H', (round, w)))

        greenletPacker(Greenlet(loopWrapper(getWithProcessing(round, secondbinValues, secondcallBackWaiter))),
            'pace_crain_low_threshold_consensus.loopWrapper(getWithProcessing(round, binValues, callBackWaiter))',
                    (pid, N, t, vi, decide, broadcast, receive)).start()

        values = secondcallBackWaiter[round].get()

        
        # Here corresponds to a proof that if one party decides at round r,
        # then in all the following rounds, everybody will propose r as an estimation. (Lemma 2, Lemma 1)
        # An abandoned party is a party who has decided but no enough peers to help him end the loop.
        # Lemma: # of abandoned party <= t
        if decided:  # infinite-message fix
            break
        

        if len(values)==1 and values[0] != 2: # fast path
            # decide s
            if not decided:
                globalState[pid] = "%d" % values[0]
                decide.put(values[0])
                decided = True
                decidedNum = values[0]
                est = values[0]
                if pid == 0:
                    print "[PID: %d] Protocol ends with value: %d, round: %d" %(pid,values[0],round)

        else:
            s = coin(round)
            if len(values) == 2 and 2 in values:
                if 1 in values:
                    est = 1 
                if 0 in values:
                    est = 0 
            else:
                est = s



def pace_biased_crain_high_threshold_consensus(instance, pid, N, t, vi, mi, decide, broadcast, receive):
    '''
    Crain's binary consensus with high threshold common coins: It takes an input vi and will finally write the decided value into _decide_ channel.
    :param pid: my id number
    :param N: the number of parties
    :param t: the number of byzantine parties
    :param vi: input value, an integer
    :param mi: carry over value, 0, 1, or 2 (\bot in the protocol)
    :param decide: deciding channel
    :param broadcast: broadcast channel
    :param receive: receive channel
    :return:
    '''
    
    # Messages received are routed to either a shared coin, the broadcast, or AUX
    coinQ = Queue(1)
    bcQ = defaultdict(lambda: Queue(1))
    auxQ = defaultdict(lambda: Queue(1))
    global supportcoin 
    supportcoin = False

    if FAILURE == 1 and pid >= 0 and pid < NumFaulty:
        vi = 1 - vi 
    elif FAILURE == 2 and pid >= 0 and pid < NumFaulty:
        vi = 0 

    def _recv():
        while True:  #not finished[pid]:
            (i, (tag, m)) = receive()
            if tag == 'B':
                # Broadcast message
                r, msg = m
                greenletPacker(Greenlet(bcQ[r].put, (i, msg)),
                    'pace_biased_crain_high_threshold_consensus.bcQ[%d].put' % r, (pid, N, t, vi, mi, decide, broadcast, receive)).start() 
            elif tag == 'C':
                # A share of a coin
                greenletPacker(Greenlet(coinQ.put, (i, m)),
                    'pace_biased_crain_high_threshold_consensus.coinQ.put', (pid, N, t, vi, mi, decide, broadcast, receive)).start()
            elif tag == 'A':
                # Aux message
                r, msg = m
                greenletPacker(Greenlet(auxQ[r].put, (i, msg)),
                      'pace_biased_crain_high_threshold_consensus.auxQ[%d].put' % r, (pid, N, t, vi, mi, decide, broadcast, receive)).start()
                pass


    greenletPacker(Greenlet(_recv), 'pace_biased_crain_high_threshold_consensus._recv', (pid, N, t, vi, mi, decide, broadcast, receive)).start()

    def brcast_get(r):
        def _recv(*args, **kargs):
            return bcQ[r].get(*args, **kargs)

        return _recv

    received = [defaultdict(set), defaultdict(set), defaultdict(set)]

    coin = high_shared_coin(instance, pid, N, t, makeBroadcastWithTag('C', broadcast), coinQ.get)
    #print coin(1)

    def getWithProcessing(r, binValues, callBackWaiter):
        def _recv(*args, **kargs):
            sender, v = auxQ[r].get(*args, **kargs)
            assert v in (0, 1) # 2 for \bot value
            assert sender in range(N)
            #if sender == 0:
            #    print ("[%d] received %d from node 0" %(pid,v))

            received[v][r].add(sender)

            # Check if conditions are satisfied
            threshold = N - t  # 2*t + 1 # N - t
            

            if True: 
                if len(binValues) == 1:
                    if len(received[binValues[0]][r]) >= threshold and not callBackWaiter[r].full():
                        # Check passed
                        callBackWaiter[r].put(binValues)
                elif len(binValues) == 2:
                    if len(received[0][r].union(received[1][r])) >= threshold and not callBackWaiter[r].full():
                        callBackWaiter[r].put(binValues)
                    elif len(received[0][r]) >= threshold and not callBackWaiter[r].full():
                        callBackWaiter[r].put([0])
                    elif len(received[1][r]) >= threshold and not callBackWaiter[r].full():
                        callBackWaiter[r].put([1])
                
            return sender, v

        return _recv

    round = 0
    est = vi
    decided = False
    decidedNum = 0      
        

    callBackWaiter = defaultdict(lambda: Queue(1))

    
    binValues = []
    while True: # checkFinishedWithGlobalState(N): <- for distributed experiment we don't need this
        round += 1
        bvOutputHolder = Queue(2)  # 2 possible values
        #print "PID %d, round %d"%(pid,round)
        # Broadcast EST
        # TODO: let bv_broadcast receive
        

        if FAILURE == 1 and pid >= 0 and pid < NumFaulty:
            est = 1 - est 
        elif FAILURE == 2 and pid >= 0 and pid < NumFaulty:
            est = 0 


        def bvOutput(m):
            if not m in binValues:
                binValues.append(m)
                bvOutputHolder.put(m)
    

        if 1-est in binValues:
            binValues = [] 
            binValues.append(est)
            bvOutputHolder.put(est)
        elif est in binValues:
            bvOutputHolder.put(est)


        def getRelease(channel):
            def _release():
                greenletPacker(Greenlet(garbageCleaner, channel),
                    'pace_biased_crain_high_threshold_consensus.garbageCleaner', (pid, N, t, vi, decide, broadcast, receive)).start()
            return _release


        if round == 1 and est == 1:
            bvOutput(1)

        br1 = greenletPacker(Greenlet(
            s_broadcast(
                1,pid, N, t, round, supportcoin, makeBroadcastWithTagAndRound('B', broadcast, round),
                brcast_get(round), bvOutput, getRelease(bcQ[round])),
            est), 'pace_biased_crain_high_threshold_consensus.s_broadcast(%d, %d, %d)' % (pid, N, t), (pid, N, t, round, vi, mi, decide, broadcast, receive))
        br1.start()
        
        w = bvOutputHolder.get()  # Wait until output is not empty

        if FAILURE == 1 and pid >= 0 and pid < NumFaulty:
            w = 1 - w 
        elif FAILURE == 2 and pid >= 0 and pid < NumFaulty:
            w = 0 

        broadcast(('A', (round, w)))
        
        
        greenletPacker(Greenlet(loopWrapper(getWithProcessing(round, binValues, callBackWaiter))),
            'pace_biased_crain_high_threshold_consensus.loopWrapper(getWithProcessing(round, binValues, callBackWaiter))',
                    (pid, N, t, vi, decide, broadcast, receive)).start()

        values = callBackWaiter[round].get()  # wait until the conditions are satisfied
        


        if round == 1:
            s = 1
        else:
            s = coin(round)
        # Here corresponds to a proof that if one party decides at round r,
        # then in all the following rounds, everybody will propose r as an estimation. (Lemma 2, Lemma 1)
        # An abandoned party is a party who has decided but no enough peers to help him end the loop.
        # Lemma: # of abandoned party <= t
        if decided:  # infinite-message fix
            break
        

        if len(values)==1:
            if values[0] == s:
                # decide s
                if not decided:
                    globalState[pid] = "%d" % s
                    decide.put(s)
                    decided = True
                    decidedNum = s
                    if pid == 0:
                        print "[PID: %d] Protocol ends with value: %d, round: %d" %(pid,s,round)
                supportcoin = True

            else:
                supportcoin = False
                pass
               
            est = values[0]

        else:
            supportcoin = True
            est = s



def pace_biased_crain_low_threshold_consensus(instance, pid, N, t, vi, mi, decide, broadcast, receive):
    '''
    Crain's binary consensus with low threshold common coins: It takes an input vi and will finally write the decided value into _decide_ channel.
    Crain's protocol relies on weak coins. We use low threshold prf instead. 
    We also implement the fast path presented in ADKG paper
    :param pid: my id number
    :param N: the number of parties
    :param t: the number of byzantine parties
    :param vi: input value, an integer
    :param mi: carry over value, 0, 1, or 2 (\bot in the protocol)
    :param decide: deciding channel
    :param broadcast: broadcast channel
    :param receive: receive channel
    :return:
    '''
    
    # Messages received are routed to either a shared coin, the broadcast, or AUX
    coinQ = Queue(1)
    bcQ = defaultdict(lambda: Queue(1))
    auxQ = defaultdict(lambda: Queue(1))
    sbcQ = defaultdict(lambda: Queue(1))

    if FAILURE == 1 and pid >= 0 and pid < NumFaulty:
        vi = 1 - vi 
    elif FAILURE == 2 and pid >= 0 and pid < NumFaulty:
        vi = 0 

    def _recv():
        while True:  #not finished[pid]:
            (i, (tag, m)) = receive()
            if tag == 'B' :
                # Broadcast message
                r, msg = m
                greenletPacker(Greenlet(bcQ[r].put, (i, msg)),
                    'pace_biased_crain_low_threshold_consensus.bcQ[%d].put' % r, (pid, N, t, vi, mi, decide, broadcast, receive)).start() 
            elif tag == 'G' :
                # Broadcast message
                r, msg = m
                greenletPacker(Greenlet(sbcQ[r].put, (i, msg)),
                    'pace_biased_crain_low_threshold_consensus.bcQ[%d].put' % r, (pid, N, t, vi, mi, decide, broadcast, receive)).start() 
            elif tag == 'C':
                # A share of a coin
                greenletPacker(Greenlet(coinQ.put, (i, m)),
                    'pace_biased_crain_low_threshold_consensus.coinQ.put', (pid, N, t, vi, mi, decide, broadcast, receive)).start()
            elif tag == 'A' or tag == 'H':
                # Aux message
                r, msg = m
                greenletPacker(Greenlet(auxQ[r].put, (i, msg)),
                      'pace_biased_crain_low_threshold_consensus.auxQ[%d].put' % r, (pid, N, t, vi, mi, decide, broadcast, receive)).start()
                pass


    greenletPacker(Greenlet(_recv), 'pace_biased_crain_low_threshold_consensus._recv', (pid, N, t, vi, mi, decide, broadcast, receive)).start()

    def brcast_get(r):
        def _recv(*args, **kargs):
            return bcQ[r].get(*args, **kargs)

        return _recv
    
    def second_brcast_get(r):
        def _recv(*args, **kargs):
            return sbcQ[r].get(*args, **kargs)

        return _recv

    received = [defaultdict(set), defaultdict(set), defaultdict(set)]

    coin = shared_coin(instance, pid, N, t, makeBroadcastWithTag('C', broadcast), coinQ.get)

    def getWithProcessing(r, binValues, callBackWaiter):
        def _recv(*args, **kargs):
            sender, v = auxQ[r].get(*args, **kargs)
            assert v in (0, 1) # 2 for \bot value
            assert sender in range(N)
            #if sender == 0:
            #    print ("[%d] received %d from node 0" %(pid,v))

            received[v][r].add(sender)

            # Check if conditions are satisfied
            threshold = N - t  # 2*t + 1 # N - t
            

            if True: 
                if len(binValues) == 1:
                    if len(received[binValues[0]][r]) >= threshold and not callBackWaiter[r].full():
                        # Check passed
                        callBackWaiter[r].put(binValues)
                elif len(binValues) == 2:
                    if len(received[0][r].union(received[1][r])) >= threshold and not callBackWaiter[r].full():
                        callBackWaiter[r].put(binValues)
                    elif len(received[0][r]) >= threshold and not callBackWaiter[r].full():
                        callBackWaiter[r].put([0])
                    elif len(received[1][r]) >= threshold and not callBackWaiter[r].full():
                        callBackWaiter[r].put([1])
                
            return sender, v

        return _recv
    

    round = 0
    est = vi
    decided = False
    decidedNum = 0      
        

    callBackWaiter = defaultdict(lambda: Queue(1))

    
    while True: # checkFinishedWithGlobalState(N): <- for distributed experiment we don't need this
        round += 1
        
        #print "PID %d, round %d"%(pid,round)
        # Broadcast EST
        # TODO: let bv_broadcast receive
        bvOutputHolder = Queue(2)  # 2 possible values
        binValues = []

        if FAILURE == 1 and pid >= 0 and pid < NumFaulty:
            est = 1 - est 
        elif FAILURE == 2 and pid >= 0 and pid < NumFaulty:
            est = 0 


        def bvOutput(m):
            if not m in binValues:
                binValues.append(m)
                bvOutputHolder.put(m)


        def getRelease(channel):
            def _release():
                greenletPacker(Greenlet(garbageCleaner, channel),
                    'pace_biased_crain_low_threshold_consensus.garbageCleaner', (pid, N, t, vi, decide, broadcast, receive)).start()
            return _release
        
        if round == 1 and est == 1:
            bvOutput(1)

        # we reuse the s_broadcast channel, and simply set supportcoin to false so that every node braodcasts its value
        br1 = greenletPacker(Greenlet(
            s_broadcast(
                1,pid, N, t, round, False, makeBroadcastWithTagAndRound('B', broadcast, round),
                brcast_get(round), bvOutput, getRelease(bcQ[round])),
            est), 'pace_biased_crain_low_threshold_consensus.s_broadcast(%d, %d, %d)' % (pid, N, t), (pid, N, t, round, vi, mi, decide, broadcast, receive))
        br1.start()
        
        w = bvOutputHolder.get()  # Wait until output is not empty

        if FAILURE == 1 and pid >= 0 and pid < NumFaulty:
            w = 1 - w 
        elif FAILURE == 2 and pid >= 0 and pid < NumFaulty:
            w = 0 

        broadcast(('A', (round, w)))
        
        
        greenletPacker(Greenlet(loopWrapper(getWithProcessing(round, binValues, callBackWaiter))),
            'pace_biased_crain_low_threshold_consensus.loopWrapper(getWithProcessing(round, binValues, callBackWaiter))',
                    (pid, N, t, vi, decide, broadcast, receive)).start()

        values = callBackWaiter[round].get()  # wait until the conditions are satisfied
        
        #now start the 2nd round of sbv_broadcast
        auxQ = defaultdict(lambda: Queue(1))
        secondbvOutputHolder = Queue(2)  # 2 possible values
        secondbinValues = []

        def secondbvOutput(m):
            if not m in secondbinValues:
                secondbinValues.append(m)
                secondbvOutputHolder.put(m)

        if len(values) == 1:
            w = values[0]
        else:
            w = 2
        
        br1 = greenletPacker(Greenlet(
            s_broadcast(
                1,pid, N, t, round, False, makeBroadcastWithTagAndRound('G', broadcast, round),
                second_brcast_get(round), secondbvOutput, getRelease(bcQ[round])),
            w), 'pace_biased_crain_low_threshold_consensus.s_broadcast(%d, %d, %d)' % (pid, N, t), (pid, N, t, round, w, mi, decide, broadcast, receive))
        br1.start()
        
        w = secondbvOutputHolder.get()
        if FAILURE == 1 and pid >= 0 and pid < NumFaulty:
            w = 1 - w 
        elif FAILURE == 2 and pid >= 0 and pid < NumFaulty:
            w = 0 

        secondcallBackWaiter = defaultdict(lambda: Queue(1))
        broadcast(('H', (round, w)))

        greenletPacker(Greenlet(loopWrapper(getWithProcessing(round, secondbinValues, secondcallBackWaiter))),
            'pace_biased_crain_low_threshold_consensus.loopWrapper(getWithProcessing(round, binValues, callBackWaiter))',
                    (pid, N, t, vi, decide, broadcast, receive)).start()

        values = secondcallBackWaiter[round].get()

        
        # Here corresponds to a proof that if one party decides at round r,
        # then in all the following rounds, everybody will propose r as an estimation. (Lemma 2, Lemma 1)
        # An abandoned party is a party who has decided but no enough peers to help him end the loop.
        # Lemma: # of abandoned party <= t
        if decided:  # infinite-message fix
            break
        

        if len(values)==1 and values[0] != 2: # fast path
            # decide s
            if not decided:
                globalState[pid] = "%d" % values[0]
                decide.put(values[0])
                decided = True
                decidedNum = values[0]
                est = values[0]
                if pid == 0:
                    print "[PID: %d] Protocol ends with value: %d, round: %d" %(pid,values[0],round)

        else:
            if round == 1:
                s = 1
            else:
                s = coin(round)
            if len(values) == 2 and 2 in values:
                if 1 in values:
                    est = 1 
                if 0 in values:
                    est = 0 
            else:
                est = s



def pace_biased_binary_consensus_trigger(pid, broadcast):
    try:
        #print "                             !!pid", pid, currentrounds, decision 
        if currentrounds[pid] > 1 or decision[pid] == True:
            return
    except:
        pass
    broadcast_msg = makeBroadcastWithTagAndRound('B', broadcast, 1)
    broadcast_msg((1,2))



def pace_biased_binary_consensus(instance, pid, N, t, vi, mi, decide, broadcast, receive):
    '''
    Pisa binary consensus: It takes an input vi and will finally write the decided value into _decide_ channel.
    :param pid: my id number
    :param N: the number of parties
    :param t: the number of byzantine parties
    :param vi: input value, an integer
    :param mi: carry over value, 0, 1, or 2 (\bot in the protocol)
    :param decide: deciding channel
    :param broadcast: broadcast channel
    :param receive: receive channel
    :return:
    '''

    # Messages received are routed to either a shared coin, the broadcast, or AUX
    coinQ = Queue(1)
    bcQ = defaultdict(lambda: Queue(1))
    auxQ = defaultdict(lambda: Queue(1))
    
    if FAILURE == 1 and pid >= 0 and pid < NumFaulty:
        vi = 1 - vi 
    elif FAILURE == 2 and pid >= 0 and pid < NumFaulty:
        vi = 0 

    def _recv():
        while True:  #not finished[pid]:
            (i, (tag, m)) = receive()
            if tag == 'D':
                # Broadcast message
                r, msg = m
                greenletPacker(Greenlet(bcQ[r].put, (i, msg)),
                    'pace_biased_binary_consensus.bcQ[%d].put' % r, (pid, N, t, vi, mi, decide, broadcast, receive)).start() # In case they block the router
            elif tag == 'C':
                # A share of a coin
                greenletPacker(Greenlet(coinQ.put, (i, m)),
                    'pace_biased_binary_consensus.coinQ.put', (pid, N, t, vi, mi, decide, broadcast, receive)).start()
            elif tag == 'E':
                # Aux message
                r, msg, maj = m
                greenletPacker(Greenlet(auxQ[r].put, (i, msg, maj)),
                      'pace_binary_consensus.auxQ[%d].put' % r, (pid, N, t, vi, mi, decide, broadcast, receive)).start()
                pass

    greenletPacker(Greenlet(_recv), 'pace_biased_binary_consensus._recv', (pid, N, t, vi, mi, decide, broadcast, receive)).start()

    def brcast_get(r):
        def _recv(*args, **kargs):
            return bcQ[r].get(*args, **kargs)

        return _recv

    received = [defaultdict(set), defaultdict(set), defaultdict(set)]

    coin = shared_coin(instance, pid, N, t, makeBroadcastWithTag('C', broadcast), coinQ.get)
    majs = [defaultdict(set), defaultdict(set), defaultdict(set)]


    def getWithProcessing(r, svalprime, delta, majority, readytodecide, binValues, callBackWaiter):
        def _recv(*args, **kargs):
            sender, v, maj = auxQ[r].get(*args, **kargs)
            assert v in (0, 1, 2) # 2 for \bot value
            assert maj in (0, 1, 2)
            assert sender in range(N)
            
            
            received[v][r].add(sender)
            majs[v][maj].add(sender)

            # Check if conditions are satisfied
            threshold = N - t  # 2*t + 1 # N - t

            global readytodecide 

            if True: #not finished[pid]:
                if len(binValues) == 1:
                    if len(received[binValues[0]][r]) >= threshold and not callBackWaiter[r].full():
                        # Check passed
                        majority = binValues[0]
                        callBackWaiter[r].put(binValues)
                        readytodecide = True 
                elif round > 1 and (len(received[2][r]) >= threshold or len(received[0][r]) < threshold or len(received[1][r]) < threshold) and not callBackWaiter[r].full(): 
                    if len(received[0][r]) >= t+1:
                        majority = 0
                    elif len(received[1][r]) >= t+1:
                        majority = 1
                    else:
                        majority = 2
                    if len(majs[0][r]) >= threshold:
                        callBackWaiter[r].put(0)
                        if svalprime == 0:
                            readytodecide = True
                        return 
                    if len(majs[1][r]) >= threshold:
                        callBackWaiter[r].put(1)
                        if svalprime == 1:
                            readytodecide = True
                        return 
                    if len(majs[1][r].union(majs[0][r])) >= threshold:
                        tmp = []
                        tmp.append(svalprime)
                        callBackWaiter[r].put(tmp)
                        return 
                    callBackWaiter[r].put([0,1])
                elif len(binValues) == 2:
                    if len(received[0][r]) >= t+1:
                        majority = 0
                    elif len(received[1][r]) >= t+1:
                        majority = 1
                    else:
                        majority = 2
                    if len(received[0][r].union(received[1][r])) >= threshold and not callBackWaiter[r].full():
                        callBackWaiter[r].put(binValues)
                    elif len(received[0][r]) >= threshold and not callBackWaiter[r].full():
                        callBackWaiter[r].put([0])
                        readytodecide = True
                    elif len(received[1][r]) >= threshold and not callBackWaiter[r].full():
                        callBackWaiter[r].put([1])
                        readytodecide = True

            return sender, v

        return _recv

    round = 0
    est = vi
    maj = mi
    sval = 0
    decided = False
    decidedNum = 0
    global delta 
    delta = 0
    svalprime = 0

    callBackWaiter = defaultdict(lambda: Queue(1))

    while True: # checkFinishedWithGlobalState(N): <- for distributed experiment we don't need this
        round += 1
        # Broadcast EST
        # TODO: let bv_broadcast receive
        bvOutputHolder = Queue(2)  # 2 possible values
        binValues = []
        global majority 
        majority = 2
        global readytodecide 
        #readytodecide = False

        if FAILURE == 1 and pid >= 0 and pid < NumFaulty:
            est = 1 - est 
        elif FAILURE == 2 and pid >= 0 and pid < NumFaulty:
            est = 0 

        def bvOutput(msg):
            m,d = msg
            global delta
            delta = d
            
            if not m in binValues:
                binValues.append(m)
                bvOutputHolder.put(m)

        def getRelease(channel):
            def _release():
                greenletPacker(Greenlet(garbageCleaner, channel),
                    'pace_biased_binary_consensus.garbageCleaner', (pid, N, t, vi, decide, broadcast, receive)).start()
            return _release

        if round == 1 and est == 1: #broadcast 1 directly
            bvOutput((1,1))
            delta = 1
            readytodecide = True

        br1 = greenletPacker(Greenlet(
            pace_bv_broadcast(
                2,pid, N, t, round,  makeBroadcastWithTagAndRound('D', broadcast, round),
                brcast_get(round), bvOutput, getRelease(bcQ[round])),
            est,maj,sval), 'pace_biased_binary_consensus.pace_bv_broadcast(%d, %d, %d)' % (pid, N, t), (pid, N, t, round, vi, mi, decide, broadcast, receive))
        br1.start()

        
        w = bvOutputHolder.get()  # Wait until output is not empty
        if FAILURE == 1 and pid >= 0 and pid < NumFaulty:
            w = 1 - w 
        elif FAILURE == 2 and pid >= 0 and pid < NumFaulty:
            w = 0 

        if decided:
            broadcast(('E', (round, decidedNum, decidedNum)))
        else:
            if delta == 1:
                broadcast(('E', (round, w, w)))
            else:
                broadcast(('E', (round, 2, w)))

        
        greenletPacker(Greenlet(loopWrapper(getWithProcessing(round, svalprime, delta, majority, readytodecide, binValues, callBackWaiter))),
            'pace_biased_binary_consensus.loopWrapper(getWithProcessing(round, svalprime, binValues, callBackWaiter))',
                    (pid, N, t, vi, decide, broadcast, receive)).start()

        values = callBackWaiter[round].get()  # wait until the conditions are satisfied
        if round == 1:
            s = 1
        else:
            s = coin(round)

        svalprime = s 

        
        # Here corresponds to a proof that if one party decides at round r,
        # then in all the following rounds, everybody will propose r as an estimation. (Lemma 2, Lemma 1)
        # An abandoned party is a party who has decided but no enough peers to help him end the loop.
        # Lemma: # of abandoned party <= t
        if decided: #and decidedNum == s:  # infinite-message fix
            break
        if len(values) == 1:
            if values[0] == s and readytodecide == True:
                # decide s
                if not decided:
                    globalState[pid] = "%d" % s
                    #print globalState
                    decide.put(s)
                    decided = True
                    decidedNum = s
                    if pid == 0:
                        print "[PID: %d] Biased Protocol ends with value: %d, round: %d" %(pid,s,round)

            else:
                pass
               
            est = values[0]
            maj = est
        else:
            est = s
            if round == 1:
                #majority = s
                maj = s
            else:
                maj = majority
        sval = s

            
        
