######################################################################################
# sarb Environment setup with Fabric (REQUIRED Python 2.5-2.7))                      #
######################################################################################


from __future__ import with_statement
from fabric.api import *
from fabric.contrib.console import confirm
from fabric.contrib.files import sed
from fabric.colors import green,blue,yellow,red
from fabric.operations import prompt,put
from fabric.context_managers import lcd
import os.path
import time


# all these can be set on command line with options -H for host
# and password is automatically prompted if not provided
# env.hosts = ['sarb']
# env.user = ['root']
# env.passoword = ['password']


CASS_YAML_FILE = '/etc/cassandra/conf/cassandra.yaml'
INSTALL_DIR = '/opt/sainath/sarb'
CASS_DATA_DIR = INSTALL_DIR + '/cassandra/data'
CASS_LOG_DIR = INSTALL_DIR + '/cassandra/commitlog'
CASS_CACHE_DIR = INSTALL_DIR +'/cassandra/saved_caches'
env.colorize_errors = True

def set_user_keys():
    user = prompt("What's the user that you want to use for this machine {} ?".format(env.host))
    env.user = user
    key_file = prompt("Where's tht key file (Private)  of this user: {} located at ?".format(user))
    env.key_filename= key_file

@task
def printdir():
    """
    Test function
    """
    user = prompt("What's the user that you want to use for this machine {} ?".format(env.host))
    env.user = user
    key_file = prompt("Where's tht key file (Private)  of this user: {} located at ?".format(user))
    env.key_filename= key_files
    x = {'this':1}
    y = sudo("hostname")
    print y
    for key in x:
        print key


# @task
# def set_hosts_user(lookup_param):
#     """
#     Second option to specify hosts on a per task basis ex:  $ fab set_hosts:<host_list>  <func_name>
#     """
#     # call above from command line to
#     # get the dynamic list of hosts to execute a task(setup cassnadra etc.) on the host
#     env.hosts = external_datastore.query(lookup_param)

# the seedlist arg is default when configuring an initial node for the cluster .. after this task takes coma seperated list of cass seed nodes
# providing atleast 2 is the best practice
def configure_cass(seedlist):
    """
    For making initial configuration to cassandra
    """
    agree = False
    while agree == False :
        CASS_DATA_DIR_NEW = prompt("Where do you want to place cassandra DATA for host {}? ... use SSD's or RAID 0".format(env.host), default = CASS_DATA_DIR)
        CASS_LOG_DIR_NEW =  prompt("Where do you want to place cassandra LOG files for host {}? \n ....... ideal to use a seperate physical device".format(env.host), default = CASS_LOG_DIR)
        CASS_CACHE_DIR_NEW = prompt("Where do you want to place cassandra CACHE for host {}? ".format(env.host), default = CASS_CACHE_DIR)
        print CASS_DATA_DIR_NEW
        print CASS_LOG_DIR_NEW
        print CASS_CACHE_DIR_NEW
        agree = confirm("Are these directories corret ?", default = False)
        if agree != True :
            print "Enter the directories correctly!"


    sudo("mkdir -p %s" % (CASS_DATA_DIR_NEW))
    sudo("mkdir -p %s" % (CASS_LOG_DIR_NEW))
    sudo("mkdir -p %s" % (CASS_CACHE_DIR_NEW))
    sudo("chown -R cassandra:cassandra %s" % (CASS_DATA_DIR_NEW))
    sudo("chown -R cassandra:cassandra %s" % (CASS_LOG_DIR_NEW))
    sudo("chown -R cassandra:cassandra %s" % (CASS_CACHE_DIR_NEW))

    if(CASS_DATA_DIR != CASS_DATA_DIR_NEW):
        # mkdir the ln first
        sudo("ln -s {} {}".format(CASS_DATA_DIR_NEW, CASS_DATA_DIR))

    if(CASS_LOG_DIR != CASS_LOG_DIR_NEW):
        sudo("ln -s {} {}".format(CASS_LOG_DIR_NEW, CASS_LOG_DIR))

    if(CASS_CACHE_DIR != CASS_CACHE_DIR_NEW):
        sudo("ln -s {} {}".format(CASS_CACHE_DIR_NEW, CASS_CACHE_DIR))
    
    sed(CASS_YAML_FILE,
        'cluster_name: .*',
        'cluster_name: sarbCassCluseter',
        use_sudo = True)
    sed(CASS_YAML_FILE,
        'tombstone_failure_threshold: .*',
        'tombstone_failure_threshold: 100000',
        use_sudo = True)
    sed(CASS_YAML_FILE,
        'commitlog_directory: .*',
        'commitlog_directory: '+CASS_LOG_DIR_NEW, use_sudo = True)
       sed(CASS_YAML_FILE,
        '/var/lib/cassandra/data',
    CASS_DATA_DIR_NEW,
        use_sudo = True)  # setting multiple locations for data ... cass will split evenly Next option would be RAID     
       sed(CASS_YAML_FILE,
        'saved_caches_directory: .*',
        'saved_caches_directory: '+CASS_CACHE_DIR_NEW,
        use_sudo = True)
       sed(CASS_YAML_FILE,
        '- seeds: .*',
        '- seeds: \"{}\"'.format(seedlist),
        use_sudo = True)
       x = sudo("hostname")
    x = prompt("Whats the listen_address & rpc_address ?.. \nPrivate IP is recommended if all nodes are in same region in Google/AWS \n Else leave it blank", default = x)
    sed(CASS_YAML_FILE,
        'listen_address: .*',
        "listen_address: {}".format(x),
        use_sudo = True)
    
    sed(CASS_YAML_FILE,
        'rpc_address: .*',
        "rpc_address: {}".format(x),
        use_sudo = True)

@task
def setup_cassandra(cassseedlist = '127.0.0.1'):
    """
    Takes as input seedlist(only for cluster setups) for local installation no need to specify     
    """
    set_user_keys()  
    sudo("echo -e '[datastax] \nname \= DataStax Repo for Apache Cassandra\nbaseurl = http://rpm.datastax.com/community\nenabled = 1\ngpgcheck = 0' | tee  /etc/yum.repos.d/datastax.repo")
    sudo("yum install dsc21")
    sudo("yum install cassandra21-tools")
    sudo("swapoff --all")  # recommended setting
    configure_cass(cassseedlist)
    start_cassandra()
    seed = cassseedlist.split(",")[0]
    fresh = prompt("Is it the first node of a fresh cluster installation? y/n")
    if(fresh == 'y'):
        time.sleep(30)
        with cd("/tmp/"):
            put("./CreateTables.cql", ".", use_sudo = True)
            sucess = sudo("cqlsh {} -f CreateTables.cql".format(env.host))
@task
def start_cassandra():
    set_user_keys()
    sudo("service cassandra start")

@task
def stop_cassandra():
    set_user_keys()
    sudo("service cassandra stop")

@task
def setup_spark():
    """
    installing spark 1.4.1
    """
    global INSTALL_DIR
    set_user_keys()
    #install_common_dependencies()

    INSTALL_DIR = prompt("What dir do you want to use for spark ? ", default = INSTALL_DIR)
    sudo("mkdir -p {}".format(INSTALL_DIR))
    master = ''
    hosts = []
    slaves = []
    with lcd('/tmp'):
        local("wget http://apache.cs.utah.edu/spark/spark-1.4.1/spark-1.4.1.tgz")
        local("tar -xvf spark-1.4.1.tgz")
        print blue("Building spark ... Approx wait time is 25 minutes... sit back and relax :)\n")
        with lcd('./spark-1.4.1/'):
            local('./build/mvn  -Dscala-2.11 -DskipTests clean package')
            local("cp conf/spark-defaults.conf.template conf/spark-defaults.conf")
            local("cp conf/spark-env.sh.template conf/spark-env.sh")
            local("printf '\n' | tee -a ./conf/spark-env.sh")
            print green("this")
            print green("Which hosts do you want to select as the master?")
            hosts = env.hosts        
            for h in hosts:
                print h
            master = prompt("Enter the IP here ->", default = '127.0.0.1')
            slaves = hosts.remove(master)    
            if slaves == None :
                print "Slaves is empty"
                slaves = [master]
                print slaves
            with open('./spark-master-ip.txt', 'a') as f:
                f.write('{}\n'.format(master))
            with open('./spark-slaves-ip.txt', 'a') as f:
                for salve in slaves:
                    f.write('{}\n'.format(salve))
        local("tar -cvf spark-1.4.1.tar spark-1.4.1")
        put("spark-1.4.1.tar", INSTALL_DIR, use_sudo = True)

    with cd(INSTALL_DIR):
        sudo("tar -xvf spark-1.4.1.tar")
        sudo("ln -s {}/spark-1.4.1 {}/spark".format(INSTALL_DIR, INSTALL_DIR))
        sudo("printf 'export SPARK_HOME={}/spark-1.4.1\n' | tee -a ~/.bashrc".format(INSTALL_DIR))
        sudo("printf 'export PATH=$PATH:$SPARK_HOME/bin\n' | tee -a ~/.bashrc")
        if env.host != master or [master] == slaves:
            numWorker = prompt ("How many worker instances do you want to run on each node?" , default = 1)
            numCores = prompt("How many cores for each worker instance?", default = 1)
            workerMem = prompt("How much memory for each worker instance? ex: 512m, 1g,  etc", default = '1g')
            sudo("printf 'export SPARK_MASTER_IP={}\n' | tee -a {}/spark-1.4.1/conf/spark-env.sh".format(master, INSTALL_DIR))
            sudo("printf 'export SPARK_WORKER_CORES={}\n' | tee -a {}/spark-1.4.1/conf/spark-env.sh".format(numCores, INSTALL_DIR))    
            sudo("printf 'export SPARK_WORKER_INSTANCES={}\n' | tee -a {}/spark-1.4.1/conf/spark-env.sh".format(numWorker, INSTALL_DIR))
            sudo("printf 'export SPARK_WORKER_MEMORY={}\n' | tee -a {}/spark-1.4.1/conf/spark-env.sh".format(workerMem, INSTALL_DIR))
            sudo("printf 'export SPARK_WORKER_PORT={}\n' | tee -a {}/spark-1.4.1/conf/spark-env.sh".format(2180, INSTALL_DIR))
            sudo("printf 'export SPARK_MASTER_WEBUI_PORT={}\n' | tee -a {}/spark-1.4.1/conf/spark-env.sh".format(8181, INSTALL_DIR))
            sudo("printf 'export SPARK_WORKER_WEBUI_PORT={}\n' | tee -a {}/spark-1.4.1/conf/spark-env.sh".format(9191, INSTALL_DIR))                
        sudo("source ~/.bashrc")        
        if env.host == master :    
            for slave in slaves:
                sudo("printf '{}' | tee -a $SPARK_HOME/conf/slaves".format(slave))
    

@task
def start_spark_cluster():
    """
    Use this function to start the spark cluster after setting up one
    """
    set_user_keys()
    with open("./spark-master-ip.txt") as f:
         master = f.readline().strip()
        env.hosts=[master]
    start_master()
    slaves = []
    with open("./spark-slaves-ip.txt") as f:
        for line in f:
             slaves.append(line.strip())
    env.hosts=slaves
    start_slaves()


@task
def start_slaves():
    """
    DONOT Use this . Its only a helper for start_spark_cluster
    Use start_spark_cluster instead
    """
    set_user_keys()
    master = ''
    with open("./spark-master-ip.txt") as f:
         master = f.readline().strip()
    sudo("source ~/.bashrc")
    with cd("$SPARK_HOME"):
        sudo("./sbin/start-slave.sh spark://{}:7077".format('sarb-cass-0'))    

@task
def start_master():
    """
    DONOT Use this . Its only a helper for start_spark_cluster
    Use start_spark_cluster instead
    """
    set_user_keys()
    sudo("source ~/.bashrc")
    with cd("$SPARK_HOME"):
        sudo("./sbin/start-master.sh")
# @parallel
# def setup_spark_job_server():

@parallel
def setup_spark_cassandra_node():
    """
    This task installs both cassandra and spark
    """
    set_user_keys()
    setup_spark()
    setup_cassandra()

def set_clock():
    sudo("timedatectl set-timezone America/New_York")
    sudo("yum install -y ntp")
    sudo("systemctl enable ntpd")
    sudo("systemctl start ntpd")

@task
def install_common_dependencies():
    """
    Installs wget, java(Oracle JDK 8), nmap wget and other tools
    """
    set_user_keys()
    set_clock()
    sudo("yum install wget")
    sudo("yum install telnet")
    sudo("yum install net-tools")
    sudo("yum install lsof")
    sudo("yum install traceroute")
    sudo("yum install nmap")
    sudo("yum groupinstall \'Development Tools\'")
    install_java()


def install_sbt():
    """
    Installs SBT(Scala build tool) locally to build spark apps and kafka source
    """
    sudo("curl https://bintray.com/sbt/rpm/rpm | sudo tee /etc/yum.repos.d/bintray-sbt-rpm.repo")
    sudo("yum install sbt")

def install_java():
    with cd('/tmp'):
        sudo('wget --no-cookies --no-check-certificate --header "Cookie: gpw_e24=http%3A%2F%2Fwww.oracle.com%2F; oraclelicense=accept-securebackup-cookie" "http://download.oracle.com/otn-pub/java/jdk/8u66-b17/jdk-8u66-linux-x64.tar.gz"')
        sudo("tar xzf jdk-8u66-linux-x64.tar.gz")
        sudo("mv jdk1.8.0_66 /opt/")
        sudo("alternatives --install /usr/bin/java java /opt/jdk1.8.0_66/bin/java 1")
        sudo("alternatives --install /usr/bin/jar jar /opt/jdk1.8.0_66/bin/jar 1")
        sudo("alternatives --install /usr/bin/javac javac /opt/jdk1.8.0_66/bin/javac 1")
        sudo("alternatives --set jar /opt/jdk1.8.0_66/bin/jar")
        sudo("alternatives --set javac /opt/jdk1.8.0_66/bin/javac")
        sudo("alternatives --set java /opt/jdk1.8.0_66/bin/java")
        sudo("printf '#JAVA \n' | tee -a ~/.bashrc")
        sudo("printf 'export JAVA_HOME=/opt/jdk1.8.0_66\n' | tee -a ~/.bashrc")
        sudo("printf 'export JRE_HOME=/opt/jdk1.8.0_66/jre\n' | tee -a ~/.bashrc")
        sudo("printf 'export PATH=$PATH:/opt/jdk1.8.0_66/bin:/opt/jdk1.8.0_66/jre/bin\n' | tee -a ~/.bashrc")
        sudo("source ~/.bashrc")

@task
def install_git():
    sudo("yum install git")

@task
def setup_spark_job_server(spark_master_url, web_url_port):
    """
    Installs spark job server that uses the spark master running at spark_master_url
    deploy hosts is a host ip
    """
    # spark master url ex: spark://64.182.212.39:7077
    set_user_keys()
    deploy_hosts = env.hosts
        global INSTALL_DIR

    install_sbt()
    install_git()
    JOB_SERVER_INSTALL_DIR = prompt("Where do you want to place the job server at ?", default=INSTALL_DIR)
    sudo("mkdir -p {}".format(JOB_SERVER_INSTALL_DIR))
    with cd('/tmp'):
        sudo('git clone -b jobserver-0.6.0-spark-1.4.1 https://github.com/spark-jobserver/spark-jobserver.git')
        with cd('./spark-jobserver'):
            sudo("sbt assembly")
            sudo("cp ./job-server/src/main/resources/application.conf ./config/sarb_spark_jobserver.conf")
            sudo("cp config/local.sh.template ./config/sarb_spark_jobserver.sh")
            # configure sarb_spark_jobserver.conf
            CONFIG_FILE = 'config/sarb_spark_jobserver.conf'
            ENV_FILE = 'config/sarb_spark_jobserver.sh'
            sed(CONFIG_FILE,
                "master = \".*",
                "master = \""+spark_master_url+'"',
                use_sudo =True)
            sed(CONFIG_FILE,
                "port = .*",
                "port = 8090",
                use_sudo =True)
            sed(CONFIG_FILE,
                "rootdir = /tmp",
                "rootdir = " + INSTALL_DIR,
                use_sudo =True)
            sed(CONFIG_FILE,
                "webUrlPort = .*",
                "webUrlPort = "+ `web_url_port`,
                use_sudo =True)    
            # configure sarb_spark_jobserver.sh
            sed(ENV_FILE,
                'SCALA_VERSION=.*',
                'SCALA_VERSION=2.11.6',
                use_sudo =True)
            sed(ENV_FILE,
                'INSTALL_DIR=.*',
                'INSTALL_DIR='+'/job-server',
                use_sudo =True)
            deploy_string = '\"'
            for host in deploy_hosts:
                deploy_string += '\n\t{}'.format(host)

            sed(ENV_FILE,
                'DEPLOY_HOSTS=.*',
                 "DEPLOY_HOSTS=\""+deploy_string+"\"",
                use_sudo = True)
            sed(ENV_FILE,
                'hostname2.net\"',
                '',
                use_sudo =True)            
            sudo("./bin/server_package.sh sarb_spark_jobserver")

def save_host_ids(h, file):
    with open(file, 'a') as f:
        for key, value in h.iteritems():
            f.write('{} {}\n'.format(key,value))

@task
def setup_zookeeper(config_file_path):
    """
    Installs zookeepr on given list of hosts
    input: zoo cfg path
    output: zoo_server_ids.txt
    """
    global INSTALL_DIR
    INSTALL_DIR = prompt("What dir do you want to use for zookeepr ? ", default = INSTALL_DIR)
    sudo("mkdir -p {}".format(INSTALL_DIR))
    ZOO_DIR = INSTALL_DIR + "/zookeeper-3.4.7"
    dataDir = prompt("what folder do you wnat to place data of zookeeper in ?", default = "/var/lib/zookeeper")

    # if env.host != '127.0.0.1':
    #     install_common_dependencies()
    # install_java()
    hosts = env.hosts
    nodes_with_zoo = {}  # if any already exist we have to assign a unique id other than the one already there
    max_zoo_id = 0
    if os.path.exists('./zoo_server_ids.txt'):
        nodes_with_zoo = read_server_ids('zoo_server_ids.txt')
        max_zoo_id = max(nodes_with_zoo.values)
    
    new_hosts_ids = {}

    for host in hosts:
        new_hosts_ids[host] = max_zoo_id + 1
        max_zoo_id += 1

    save_host_ids(new_hosts_ids, 'zoo_server_ids.txt')

    with cd('/tmp'):
        sudo("wget http://archive.apache.org/dist/zookeeper/zookeeper-3.4.7/zookeeper-3.4.7.tar.gz")
        sudo("tar -xvf zookeeper-3.4.7.tar.gz")
        sudo("mv zookeeper-3.4.7 {}".format(INSTALL_DIR))

    with cd(ZOO_DIR):
        sudo("cp conf/zoo_sample.cfg conf/zoo.cfg")
        ZOO_CFG_FILE = '{}/conf/zoo.cfg'.format(ZOO_DIR)
        sed(ZOO_CFG_FILE,
            "dataDir=*",
            "dataDir={}".format(dataDir),
            use_sudo = True)
        sudo("printf 'export ZOOKEEPER_HOME={}\n' | tee -a ~/.bashrc".format(ZOO_DIR))
        sudo("source ~/.bashrc")

        for key, value in new_hosts_ids.iteritems():
            sudo('printf server.{}={}:2888:3888 | tee -a {}'.format(key, value,ZOO_CFG_FILE))

    sudo("ln -s {} {}".format(ZOO_DIR, INSTALL_DIR+'/zookeeper'))
    sudo("mkdir -p {}".format(dataDir))
    sudo("printf {} > {}/myid".format(new_hosts_ids[env.host], dataDir))
    with cd("$ZOOKEEPER_HOME"):
        sudo('./bin/zkServer.sh start')
    
    #perform a small test to see if zk is online
    print "Waiting \n"
    time.sleep(45)
    host = sudo("hostname")
    response = sudo("echo ruok | nc {} 2181".format(host))
    if response == 'imok':
        print green("Zookeeper is running as a service on {} port 2181".format(host))
        state = sudo("echo stat | nc {} 2181".format(host))
        print "State is :\n"
        print blue(state)
    else:
        print red("ERROR installing ZK\n")

@task
def setup_kafka(server_properties_path):
    """
    Installs kafka with zookeper also running on the same node
    Parameters : server properties file path.
    Output: kafka_server_ids.txt file
    """
    set_user_keys()
    global INSTALL_DIR
    INSTALL_DIR = prompt("What dir do you want to use for kafka ? ", default = INSTALL_DIR)
    sudo("mkdir -p {}".format(INSTALL_DIR))
    set_clock()
    hosts = env.hosts
    nodes_with_kafka = {}
    max_kafka_id = 0
    if os.path.exists('./kafka_server_ids.txt'):
        nodes_with_kafka = read_server_ids('kafka_server_ids.txt')
        max_kafka_id = max(nodes_with_kafka.values)        
    new_hosts_ids = {}    
    for host in hosts:
        new_hosts_ids[host] = max_kafka_id + 1
        max_kafka_id += 1
    
    # write these out to a file for future use
    save_host_ids(new_hosts_ids, './kafka_server_ids.txt')

    #now use these ids to setup kafka cluster or add new nodes to kafka cluster    
    if env.host != '127.0.0.1' :
        install_common_dependencies()
    install_java()
    with cd('/tmp'):
        sudo("wget http://apache.osuosl.org/kafka/0.8.2.1/kafka_2.11-0.8.2.1.tgz")
        sudo("tar -xvf kafka_2.11-0.8.2.1.tgz")
        with cd('./kafka_2.11-0.8.2.1'):
            print ""
            sudo("mv /tmp/kafka_2.11-0.8.2.1/config/server.properties.template /tmp/kafka_2.11-0.8.2.1/config/server.properties")
            put(server_properties_path, './config/server.properties', use_sudo = True)
            if os.path.exists("./zoo_server_ids.txt"):
                ids = read_server_ids('./zoo_server_ids.txt')
                x = ''
                for key in ids:
                    x += '{}:2181,'.format(key)
                
                x = x[:-1]  # strip extra coma
                host_name = sudo("hostname")
                this_host = env.host
                # change zookeper connect in server properties
                sed("/tmp/kafka_2.11-0.8.2.1/config/server.properties",
                    "zookeeper.connect=.*",
                    "zookeeper.connect={}".format(x),
                    use_sudo = True)
                sed("/tmp/kafka_2.11-0.8.2.1/config/server.properties",
                    "host.name=.*",
                    "host.name={}".format(host_name),
                    use_sudo = True)
                sed("/tmp/kafka_2.11-0.8.2.1/config/server.properties",
                    "broker.id=.*",
                    "broker.id={}".format(new_hosts_ids[this_host]),
                    use_sudo = True)
            else:
                print red("Install zookeeper first ... If you have installed it already \n make sure that zoo_server_ids.txt exists with valid entries")
                sys.exit(0)
        sudo("mv /tmp/kafka_2.11-0.8.2.1 {}".format(INSTALL_DIR))
        sudo("ln -s {}/kafka_2.11-0.8.2.1 {}/kafka".format(INSTALL_DIR, INSTALL_DIR))
        sudo("printf 'export KAFKA_HOME={}/kakfa\n' | tee -a ~/.bashrc".format(INSTALL_DIR))
        sudo("printf 'export KAFKA=$KAFKA_HOME/bin\n' | tee -a ~/.bashrc")
        sudo("printf 'export KAFKA_CONFIG=$KAFKA_HOME/config\n' | tee -a ~/.bashrc")
        sudo("source ~/.bashrc")
        sudo("nohup $KAFKA_HOME/bin/kafka-server-start.sh $KAFKA_HOME/config/server.properties >/dev/null &2>1 &")
@task
def start_zk_kafka():
	"""
	Starts zookeeper and kafka
	"""
	with cd("$ZOOKEEPER_HOME"):
        sudo('./bin/zkServer.sh start')
    
    #perform a small test to see if zk is online
    print "Waiting \n"
    time.sleep(45)
    host = sudo("hostname")
    response = sudo("echo ruok | nc {} 2181".format(host))
    if response == 'imok':
        print green("Zookeeper is running as a service on {} port 2181".format(host))
        state = sudo("echo stat | nc {} 2181".format(host))
        print "State is :\n"
        print blue(state)
        sudo("nohup $KAFKA_HOME/bin/kafka-server-start.sh $KAFKA_HOME/config/server.properties >/dev/null &2>1 &")
    else:
        print red("ERROR starting ZK\n")
	        

def read_server_ids(server_id_file):
    d = {}
    with open(server_id_file) as f:
        for line in f:
            (key, val) = line.split()
            d[key] = int(val)
    return d


@task
def update_war_gui():
    """
    puts the sarb gui tar on server (including tomcat and starts it up)  
    """
    set_user_keys()
    global INSTALL_DIR
    put("sarb.war","/mnt/ssd0/sainath/tomcat/webapps/", use_sudo=True)

@task
def setup_gui():
    """
    puts the sarb gui tar on server (including tomcat and starts it up)  
    """
    set_user_keys()
    global INSTALL_DIR
    INSTALL_DIR = prompt("Which directory do you want to place tomcat in", default = INSTALL_DIR)
    sudo("mkdir -p %s" % (INSTALL_DIR))
    put("./sarbTomcat.zip", INSTALL_DIR, use_sudo = True)
    with cd(INSTALL_DIR):
        sudo("unzip sarbTomcat.zip")
        ip = sudo("hostname -i")
        sed('{}/sarbTomcat/conf/server.xml'.format(INSTALL_DIR),
        '<Connector',
        '<Connector address=\"{}\" '.format(ip), use_sudo = True)
        sudo("{}/sarbTomcat/bin/catalina.sh start".format(INSTALL_DIR))
