# ntapfuse unit testing version 0.1
# code by @author Carter S. Levinson <carter.levinson@pitt.edu>
from operator import sub
import unittest
import subprocess
import sqlite3
import regex
import pytest
import os
import getpass


# Note: that there is shell builtin command to interface with every syscall

# Good tests can be thought of as operating in four steps
# 1. Arrange: prepare the environment for our tests
# 2. Act: the singular state changing action we want to test
# 3. Assert: examine the resulting state for expected behaviour
# 4. Cleanup: the test must leave up no trace


mountName = "mountPoint"
baseDir = "testbase"
dbName = "log.db"
blockSize = 4096
usage=0
numLogs = 0
oriDir = os.getcwd()
workDir = oriDir[:-5] if oriDir[-5:] == "/test" else oriDir
mountDir = workDir+"/%s"%mountName

userList = ["user666","user888","user999"]

# get current username
oriUser = getpass.getuser()
oriUid = os.getuid()


# setup_test_env mainly create some test users and make install
def setup_test_env():

    os.system("sudo make install")  
    print("creating some test users...")    

    for user in userList:
        cmd = '''
        sudo useradd -p $(openssl passwd -1 password) %s
        sudo adduser %s sudo
        sudo adduser %s %s
        '''%(user,user,user,oriUser)
        os.system(cmd)

def destroy_test_env():
    print("deleting all test users...")
    for user in userList:
        os.system("sudo userdel -f %s"%user)
    # go back to the test directory
    os.chdir(oriDir) 
    


# will be put at the beginning of each test. 
# It create base and mountpoint directories, and give permission to group users

def init_test():

    print("\ncreating basedir and mountpoint...")
    os.chdir("%s"%workDir)
    cmd = '''
    rm %s
    mkdir %s   
    mkdir %s
    chmod ugo+rwx %s
    chmod ugo+rwx %s
    ntapfuse mount %s %s
    chmod ugo+rwx %s
    '''%(dbName,mountName,baseDir,mountName,baseDir,baseDir,mountName,dbName)

    os.system(cmd)

# will be put at the end of each test; It removes all the test files and folders

def test_done():
    print("removing all test files and folders...")
    cmd = '''
    cd %s
    rm -r %s -f
    sudo umount %s
    rm -r %s -f
    '''%(workDir,baseDir,mountName,mountName)
    
    os.system(cmd)


def get_uid_from_username(username):
    p = subprocess.run("id -u %s"%username, shell=True,capture_output=True)
    uid = p.stdout.decode("utf-8")
    return str(int(uid))


setup_test_env()

class TestClass:

    def test_mkdir(self):

        init_test()

        testuser1 = oriUser
        testuser2 = userList[1]
        uid1 = get_uid_from_username(testuser1)
        uid2 = get_uid_from_username(testuser2)
        numLogs1 = check_log_db(uid1,"Mkdir")
        numLogs2 = check_log_db(uid2,"Mkdir")
        usage1 = check_quota_db(uid1)
        usage2 = check_quota_db(uid2)
        

        print("Testing mkdir...")
        
        cmd='''
        cd %s
        mkdir folder%s
        cd %s
        '''
        print("creating some empty folders for current user...")
        for i in range(22):
            os.system(cmd%(mountDir,i,workDir))
            numLogs1+=1
            usage1+=blockSize

       
        print("switching to another user and create some empty folders")

        cmd='''
        sudo umount %s
        rmdir %s/*
        sudo runuser %s << EOF
        ntapfuse mount %s %s
        cd %s
        mkdir folder%s
        '''

        for i in range(30,50):
            os.system(cmd%(mountName,baseDir,testuser2,baseDir,mountName,mountDir,i))
            numLogs2+=1
            usage2+=blockSize

        usageRes1 = check_quota_db(uid1)
        numLogsRes1 = check_log_db(uid1,"Mkdir")

        usageRes2 = check_quota_db(uid2)
        numLogsRes2 = check_log_db(uid2,"Mkdir")

        print("User1 expecting numbers of logs: %s  result is: %s"%(str(numLogs1),str(numLogsRes1)))
        print("User1 expecting user usage: %s  result is: %s"%(str(usage1),str(usageRes1)))
        print("User2 expecting numbers of logs: %s  result is: %s"%(str(numLogs2),str(numLogsRes2)))
        print("User2 expecting user usage: %s  result is: %s"%(str(usage2),str(usageRes2)))

        test_done()

        assert usageRes1==usage1 and numLogsRes1==numLogs1 and usageRes2==usage2 and numLogsRes2==numLogs2
        

     
    def test_rmdir(self):
        init_test()
        # need to assume mkdir work, otherwise there is no folder to delete
        print("Testing rmdir...")
        testuser1 = oriUser
        testuser2 = userList[1]
        uid1 = get_uid_from_username(testuser1)
        uid2 = get_uid_from_username(testuser2)
        numLogs1 = check_log_db(uid1,"Rmdir")
        numLogs2 = check_log_db(uid2,"Rmdir")
        usage1 = check_quota_db(uid1)
        usage2 = check_quota_db(uid2)

        cmd='''
        cd %s
        mkdir folder%s
        mkdir folder%s
        rmdir folder%s
        cd %s
        '''

        print("creating some folders and then delete some of them...")
        for i in range(18):
            os.system(cmd%(mountDir,i+18,i,i,workDir))
            numLogs1+=1
            usage1+=blockSize


        cmd='''
        sudo umount %s
        sudo runuser %s << EOF
        ntapfuse mount %s %s
        cd %s
        mkdir folder%s
        mkdir folder%s
        rmdir folder%s
        cd %s
        '''

        print("switch to another user to do the same stuff...")
        for i in range(100,120):
            os.system(cmd%(mountName,testuser2,baseDir,mountName,mountDir,i+40,i,i,workDir))
            numLogs2+=1
            usage2+=blockSize
           
        # check if usage and logs match
        
        usageRes1 = check_quota_db(uid1)
        numLogsRes1 = check_log_db(uid1,"Rmdir")

        usageRes2 = check_quota_db(uid2)
        numLogsRes2 = check_log_db(uid2,"Rmdir")

        print("User1 expecting numbers of logs: %s  result is: %s"%(str(numLogs1),str(numLogsRes1)))
        print("User1 expecting user usage: %s  result is: %s"%(str(usage1),str(usageRes1)))
        print("User2 expecting numbers of logs: %s  result is: %s"%(str(numLogs2),str(numLogsRes2)))
        print("User2 expecting user usage: %s  result is: %s"%(str(usage2),str(usageRes2)))

        test_done()
        destroy_test_env()

        assert usageRes1==usage1 and numLogsRes1==numLogs1 and usageRes2==usage2 and numLogsRes2==numLogs2


    

    def test_write(self):
        return

    def test_unlink(self):
        return

    def test_chown(self):
        return 
    
    def test_truncate(self):
        return 

    def test_read(self):
        return

    def test_utime(self):
        return 

def check_log_db(uid,op=None):
    con = sqlite3.connect(dbName)
    # uid=os.getuid()
    cur = con.cursor()
    if op:
        cur.execute("select count(*) from Logs where UID=%s and Operation='%s'"%(uid,op))
    else:
        cur.execute("select count(*) from Logs where UID=%s"%uid)
    res = cur.fetchall()
    con.close()
    try:
        return res[0][0]
    except:
        return 0
    

def check_quota_db(uid):
    con = sqlite3.connect(dbName)
    cur = con.cursor()
    cur.execute("select Usage from Quotas where UID=%s"%uid)
    res = cur.fetchall()
    con.close()
    try:
        return res[0][0]
    except:
        return 0  # return the usage of an user if valid
