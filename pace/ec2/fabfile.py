from __future__ import with_statement
from fabric.api import *
from fabric.operations import put, get
from fabric.contrib.console import confirm
from fabric.contrib.files import append
import time, sys, os, scanf
from io import BytesIO
import math

your_git_password = "XXXXX"

@parallel
def host_type():
    run('uname -s')

@parallel
def gettime():
    run('date +%s.%N')

@parallel
def checkLatency():
    '''
    PING 52.49.163.101 (52.49.163.101) 56(84) bytes of data.
    64 bytes from 52.49.163.101: icmp_seq=1 ttl=45 time=141 ms

    --- 52.49.163.101 ping statistics ---
    1 packets transmitted, 1 received, 0% packet loss, time 0ms
    rtt min/avg/max/mdev = 141.722/141.722/141.722/0.000 ms
    '''
    resDict = []
    totLen = len(env.hosts)
    for destination in env.hosts:
        waste = BytesIO()
        with hide('output', 'running'):
            res = run('ping -c 3 %s' % destination, stdout=waste, stderr=waste).strip().split('\n')[1].strip()
        # print repr(res)
        lat = scanf.sscanf(res, '%d bytes from %s icmp_seq=%d ttl=%d time=%f ms')[-1]
        resDict.append(lat)
    print (' '.join([env.host_string, str(sorted(resDict)[int(math.ceil(totLen * 0.75))]), str(sum(resDict) / len(resDict))]))

@parallel
def ping():
    run('ping -c 5 google.com')
    run('echo "synced transactions set"')
    run('ping -c 100 google.com')

@parallel
def cloneRepo():
    run('git clone anonymized link'%your_git_password)


@parallel
def addhoc():
    run('sudo lsof -t -i tcp:49500 | xargs kill -9')
    #with cd('~/beat-bft'):
    #    run ('ls')

def checkfile():
    with cd('~/pace'):
        run ('ls')

@parallel
def install_dependencies_addhoc():
    sudo('pip install greenlet --upgrade')
    sudo('pip install gevent')

@parallel
def install_dependencies():
    sudo('apt-get update')
    sudo('apt-get -y install python-gevent')
    sudo('apt-get -y install git')
    sudo('apt-get -y install make')
    #sudo('apt-get -y install python-socksipy')
    sudo('apt-get -y install python-socks')
    #sudo('apt-get -y install python-pip')
    sudo('apt-get -y install python-dev')
    sudo('apt-get -y install python-gmpy2')
    sudo('apt-get -y install flex')
    sudo('apt-get -y install bison')
    sudo('apt-get -y install libgmp-dev')
    sudo('apt-get -y install libssl-dev')
    put('./get-pip.py', '~/')
    run('python ~/get-pip.py')
    sudo('pip install greenlet')
    #sudo('pip install greenlet --upgrade')
    sudo('pip install --upgrade setuptools')
    sudo('pip install pycrypto')
    sudo('pip install pycryptodomex')
    sudo('pip install ecdsa')
    sudo('pip install zfec')
    #sudo('pip install gevent==1.1.0')
    sudo('pip install gipc==0.3.2')
    sudo('pip install pyparsing==1.5.5')
    sudo('pip install hypothesis')
    run('wget https://crypto.stanford.edu/pbc/files/pbc-0.5.14.tar.gz')
    run('tar -xvf pbc-0.5.14.tar.gz')
    with cd('pbc-0.5.14'):
        run('./configure')
        run('make')
        sudo('make install')
    with settings(warn_only=True):
        if run('test -d charm').failed:
            run('git clone https://github.com/JHUISI/charm.git')
        with cd('charm'):
            run('git checkout 2.7-dev')
            run('./configure.sh')
            sudo('python setup.py install')
    sudo('ldconfig -v')


@parallel
def prepare():
    syncKeys()
    install_dependencies()
    cloneRepo()
    git_pull()


@parallel
def stopProtocols():
    with settings(warn_only=True):
        run('killall python')
        run('killall dtach')
        run('killall server.py')

@parallel
def removeHosts():
    run('rm ~/hosts')

@parallel
def writeHosts():
    put('./hosts', '~/')

@parallel
def fetchLogs():
    get('~/msglog.TorMultiple',
        'logs/%(host)s' + time.strftime('%Y-%m-%d_%H:%M:%SZ',time.gmtime()) + '.log')

@parallel
def syncKeys():
    put('./*.keys', '~/pace2/')

import SocketServer, time
start_time = 0
sync_counter = 0
N = 1
t = 1

class MyTCPHandler(SocketServer.BaseRequestHandler):
    """
    The RequestHandler class for our server.

    It is instantiated once per connection to the server, and must
    override the handle() method to implement communication to the
    client.
    """
    def handle(self):
        # self.request is the TCP socket connected to the client
        self.data = self.rfile.readline().strip()
        print ("%s finishes at %lf" % (self.client_address[0], time.time() - start_time))
        print (self.data)
        sync_counter += 1
        if sync_counter >= N - t:
            print ("finished at %lf" % (time.time() - start_time))

def runServer():   # deprecated
    global start_time, sync_counter, N, t
    N = int(Nstr)
    t = int(tstr)
    start_time = time.time()
    sync_counter = 0
    server = SocketServer.TCPServer(('0.0.0.0', 51234), MyTCPHandler)
    server.serve_forever()

@parallel
def runProtocolFromClient(client, key):
    # s = StringIO()
    with cd('~/HoneyBadgerBFT/mmr13'):
        run('python honest_party_test_EC2.py ~/hosts %s ~/ecdsa_keys %s' % (key, client))

@parallel
def generateTX(N_, seed):
    N = int(N_)
    run('python -m pace.ec2.generate_tx %d %s > tx' % (N, seed))

@parallel
def runProtocol_local(N_, t_, B_, v_):
    N = int(N_)
    t = int(t_)
    B = int(B_) * N 
    v = int(v_)
    with shell_env(LIBRARY_PATH='/usr/local/lib', LD_LIBRARY_PATH='/usr/local/lib'):
        with cd('~/pace'):
            run('python -m pace.test.honest_party_test -k'
            ' thsig%d_%d.keys -e ecdsa%d.keys -b %d -n %d -t %d -c thenc%d_%d.keys -v %d' % (N, t, t, B, N, t, N, t, v))

@parallel
def runProtocol(N_, t_, B_, v_, timespan_, tx='tx'):
    N = int(N_)
    t = int(t_)
    B = int(B_) * N   # now we don't have to calculate them anymore
    v = int(v_)
    timespan = int(timespan_)
    print (N, t, B, timespan)
    with shell_env(LIBRARY_PATH='/usr/local/lib', LD_LIBRARY_PATH='/usr/local/lib'):
        with cd('~/pace2'):
            run('python -m pace.test.honest_party_test_EC2 -k'
            ' thsig%d_%d.keys -e ecdsa%d.keys -a %d -b %d -n %d -t %d -c thenc%d_%d.keys -v %d' % (N, t, t, timespan, B, N, t, N, t, v))
   #python -m pace.test.honest_party_test_EC2 -k thsig4_1.keys -e ecdsa1.keys -a 1 -b 10 -n 4 -t 1 -c thenc4_1.keys -v 1

@parallel
def checkout():
    run('svn checkout --no-auth-cache --username aluex --password JkJ-3pc-s3Y-prp https://subversion.assembla.com/svn/ktc-scratch/')

@parallel
def svnUpdate():
    with settings(warn_only=True):
        if run('test -d ktc-scratch').failed:
            run('svn checkout  --no-auth-cache --username aluex --password JkJ-3pc-s3Y-prp https://subversion.assembla.com/svn/ktc-scratch/')
    with cd('~/ktc-scratch'):
        run('svn up  --no-auth-cache --username aluex --password JkJ-3pc-s3Y-prp')

@parallel
def svnClean():
    with settings(warn_only=True):
        if run('test -d ktc-scratch').failed:
            run('svn checkout --username aluex --password JkJ-3pc-s3Y-prp https://subversion.assembla.com/svn/ktc-scratch/')
    with cd('~/ktc-scratch'):
        run('svn cleanup')

@parallel
def makeExecutable():
    with cd('~/ktc-scratch'):
        run('chmod +x server.py')

# http://stackoverflow.com/questions/8775598/start-a-background-process-with-nohup-using-fabric
def runbg(cmd, sockname="dtach"):  
    return run('dtach -n `mktemp -u /tmp/%s.XXXX` %s'  % (sockname,cmd))

@parallel
def startPBFT(): ######## THIS SHOULD BE CALLED IN REVERSED HOST ORDER
    with cd('~/ktc-scratch'):
        runbg('python server.py')

def startClient():
    with cd('~/ktc-scratch'):
        #batch_size = 1024
        #batch_size = 2048
        #batch_size = 4096
        #batch_size = 8192
        batch_size = 16384
        #batch_size = 65536
        run('python gen_requests.py 1000 %d' % (batch_size,))
        run('python client.py 40')
        run('python parse_client_log.py %d' % (batch_size,))

@parallel
def git_pull():
    with settings(warn_only=True):
        if run('test -d pace2').failed:
            run('git clone your_git_link'%your_git_password)
    with cd('~/pace2/'):
        run('git reset --hard origin/master')
        run('git clean -fxd')
        run('git pull')
