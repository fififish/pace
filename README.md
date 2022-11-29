# Pace Repository

- PACE: Asynchronous fault-tolerant protocols. 
- This reposity is based on HoneyBadgerBFT and BEAT
  - HoneyBadgerBFT: https://github.com/amiller/HoneyBadgerBFT
  - BEAT: https://github.com/fififish/beat

- This is an older version based on Python 2.7. We are currently working on a new library using Golang. 

- Please cite the following paper for this work:

  - Haibin Zhang and Sisi Duan. PACE: Fully Parallelizable Asynchronous BFT from Reproposable Byzantine Agreement. CCS 2022. 

### Protocols
Eight protocols are included in this repo

+ version = 1: BEAT0 (MMR) - not live
+ version = 2: ACE (Pillar)
+ version = 3: PACE (Pisa, a RABA version of Pillar)
+ version = 4: BEAT-Cobalt (Cobalt ABA)
+ version = 5：ACE (Crain20 algorithm 2 with high-threshold common coin)
+ version = 6: ACE (Crain20 algorithm 1 with low-threhsold common coin - weak coin in the original paper)
+ version = 7：PACE (RABA protocol based on Crain20 (algorithm 2 with high-threshold common coin))
+ version = 8: PACE (RABA protocol based on Crain20 (algorithm 1 with low-threhsold common coin - weak coin in the original paper))

### Installation && How to run the code

Working directory is usually the **parent directory** of pace

+ **N** means the total number of parties;
+ **t** means the tolerance, usually N=3t+1 in our experiments;
+ **B** means the maximum number of transactions committed in a block (by default N log N). And therefore each party proposes B/N transactions.
+ **v** means the version of the protocol 

#### Install dependencies 

+ required packages (via sudo apt install): python-gevent,python3-dev,python-socksipy,flex,bison,libgmp-dev,libssl-dev
```
    pip install greenlet
    pip install greenlet --upgrade
    pip install gevent
    pip install --upgrade setuptools
    pip install pycrypto
    pip install pycryptodomex 
    pip install ecdsa
    pip install zfec
    pip install gipc
```

+ Install pbc 
(in this demo version, we include pbc in the repository just in case)
    ```bash
    wget https://crypto.stanford.edu/pbc/files/pbc-0.5.14.tar.gz
    tar -xvf pbc-0.5.14.tar.gz
    cd pbc-0.5.14
    ./configure ; make ; sudo make install
    export LIBRARY_PATH=$LIBRARY_PATH:/usr/local/lib
    export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/lib
    ```

+ charm (in this demo version, we include charm in the repository as some charm versions are not compatible with our codebase)
    ```bash
    sudo apt-get install python3-dev
    git clone https://github.com/JHUISI/charm.git 
    cd charm
    git checkout 2.7-dev
    ./configure.sh
    sudo python setup.py install
    ```


Generate the keys
+ Threshold PRF Keys (used for common coins)
    ```bash
    python -m pace.commoncoin.prf_generate_keys N t+1 > thsig[N]_[t].keys
    example: python -m pace.commoncoin.prf_generate_keys 4 2 > thsig4_1.keys
    ```
+ For version = 5 and 7, the threshold t+1 should be replacd with 2*t+1
    ```bash
    example: python -m pace.commoncoin.prf_generate_keys 4 3 > thsig4_1.keys
    ```

+ ECDSA Keys
    ```bash
    python -m pace.ecdsa.generate_keys_ecdsa N > ecdsa[t].keys
    example: python -m pace.ecdsa.generate_keys_ecdsa 4 > ecdsa1.keys
    ```

+ Threshold Encryption Keys
    ```bash
    python -m pace.threshenc.generate_keys N t+1 > thenc[N]_[t].keys
    example: python -m pace.threshenc.generate_keys 4 2 > thenc4_1.keys
    ```



##### Launch the code
    python -m pace.test.honest_party_test -k thsig4_1.keys -e ecdsa1.keys -b 10 -n 4 -t 1 -c thenc4_1.keys -v 1

    When 'Consensus Finished' is printed, it means everything works well. 
    
Notice that each party will expect at least NlgN many transactions. And usually there is a key exception after they finish the consensus. Please just ignore it.

### How to deploy the Amazon EC2 experiment

Scripts could be found in the pace/ec2/ folder.
