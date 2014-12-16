#!/usr/bin/env python
# -*- coding: utf-8 -*-

import glob, os, json

from fabric.api import env, run, sudo, put, cd, lcd
from fabric.colors import blue, cyan, green, magenta, red, white, yellow

env.use_ssh_config = True

################################################################################
# -- 定数 --

_MYSQL_ROOT_PASSWD = 'AK47_kin_patsu_russia'

################################################################################

def main():
    """
    プロビジョニングを実行してね。(メインタスク)
    """
    print green('========================================')
    print green('↓↓↓ はじまるよ ↓↓↓ ')
    print green('========================================')
    install()
    setup()
    deploy()
    print blue('========================================')
    print blue('↑↑↑ おわりだよ ↑↑↑')
    print blue('========================================')


################################################################################
# install

def install():
    """
    ミドルウェアをインストールしてね。
    """
    install_basic_libs()
    install_php()
    # MySQL, nodejsを導入
    sudo('yum -y install mysql mysql-devel mysql-server')
    sudo('yum -y install --enablerepo=epel nodejs npm')
    print green('ミドルウェア入れたよ。')


def install_basic_libs():
    """
    基本ライブラリ導入
    """
    sudo('yum -y upgrade')
    sudo('yum -y groupinstall "Development Tools"')
    sudo('yum -y install libxml2-devel openssl-devel')
    sudo('yum -y install dtach')


def install_php():
    """
    PHPのインストール
    """
    # remiリポジトリ登録(php5.5を使う)
    sudo('yum install -y http://rpms.famillecollet.com/enterprise/remi-release-6.rpm', warn_only=True)
    # PHP共通ライブラリ導入
    sudo('yum -y install --enablerepo=remi-php55 php php-common php-cli php-devel php-mbstring php-xml')
    sudo('yum -y install --enablerepo=remi-php55 php-mysqlnd php-pdo')


################################################################################
# setup

def setup():
    """
    サービス設定してね。
    """
    setup_mysql()
    setup_mysql_init()
    # PHPのConfigファイル配置
    put('./conf/php/php.ini', '/etc/php.ini', use_sudo=True)
    print green('サービス設定したよ。')


def setup_mysql():
    """
    MySQL設定、サービス起動してね。
    """
    # Configファイル配置
    put('./conf/mysql/my.cnf', '/etc/my.cnf', use_sudo=True)
    # サービス起動＆自動起動設定（てきとう）
    # 止まってた場合だけ初回っぽい処理を、
    # 既に起動していれば設定ファイル反映させるために再起動
    if sudo('service mysqld status', warn_only=True) == 'mysqld is stopped':
        sudo('service mysqld start')
        sudo('chkconfig mysqld on')
    else:
        sudo('service mysqld restart')
    print green('MySQL設定・サービス起動したよ。')


def setup_mysql_init():
    """
    MySQLの初期設定してね。
    """
    # rootパスワードを変更
    passwd_change_query = "SET PASSWORD FOR root@localhost=PASSWORD('%s');" % _MYSQL_ROOT_PASSWD
    passwd_change_command = 'mysql -u root -e "%s"' % passwd_change_query
    sudo(passwd_change_command, warn_only=True)
    # 不要テーブル、ユーザ削除用sqlを実行
    tmp_sql_path = './conf/mysql/initdb.sql'
    __exec_sql_file(tmp_sql_path)
    print green('MySQL databaseを初期化したよ。')


################################################################################
## nise_bot

def deploy():
    """
    アプリケーションのセットアップしてね。
    """
    # DB定義(json)読んでね。
    basedir = 'source/bot-project/'
    db = json.load(open(basedir + 'config/db.json', 'r'))
    # database作ってね。
    __make_database(db['DBNAME'], db['USER'], db['PASS'], db['HOST'], db['CHARSET'])
    # schemeのsql流してね。
    __exec_sql_file(basedir + 'scheme/nise_bot.sql', db['DBNAME'])
    # リモートでの処理
    with cd('/source/bot-project'):
        # nodemodule入れてね。
        run('npm install')
        # logディレクトリを作って、書き込み権限つけてね。
        run('mkdir -p log/')
        # vagrantの場合mountで権限指定しちゃってるので気をつけてね。
        sudo('chmod -R 755 log/')
        # 既存の発言拾ってね。
        run('sh shell/init.sh')
        # node起動してね。
        __nohup('sh shell/async_stream.sh')
    # cron設定してね。
    put('./conf/crontab', '/tmp/crontab')
    sudo('crontab /tmp/crontab')
    sudo('service crond reload')
    print green('botのセットアップしたよ。')


def launch():
    """
    node起動するね。
    """
    with cd('/source/bot-project'):
        # 起動してたら処すね。(やさしくないね)
        sudo("kill -9 `pgrep -f 'node' `", warn_only=True)
        # node起動してね。
        __nohup('sh shell/async_stream.sh')
    print green('botデーモン起動したよ。')


################################################################################
# ライブラリ

def __exec_sql_file(sqlfile, database=""):
    """
    SQLファイルを指定して実行
    """
    tmp_sql = '/tmp/' + os.path.basename(os.path.realpath(sqlfile))
    put(sqlfile, tmp_sql)
    command = 'mysql -u root -p%s %s < %s' % (_MYSQL_ROOT_PASSWD, database, tmp_sql)
    run(command)


def __exec_sql_query(query, database=""):
    """
    指定されたSQL文を実行
    """
    command = 'mysql -u root -p%s %s -e "%s"' % (_MYSQL_ROOT_PASSWD, database, query)
    run(command)


def __make_database(name, user, passwd, host='localhost', charset='utf8'):
    """
    databaseを作成
    """
    # database作成用クエリ組み立て
    query  = "DROP DATABASE IF EXISTS %s;" % name
    query += "CREATE DATABASE %s DEFAULT CHARACTER SET %s;" % (name, charset)
    query += "GRANT ALL PRIVILEGES ON %s.* TO '%s'@'%s' IDENTIFIED BY '%s' WITH GRANT OPTION;" % (name, user, host, passwd)
    query += "FLUSH PRIVILEGES;"
    # クエリ実行
    command = 'mysql -u root -p%s -e "%s"' % (_MYSQL_ROOT_PASSWD, query)
    run(command)


def __nohup(cmd, sockname="dtach"):
    """
    nohup代替
    """
    return run('dtach -n `mktemp -u /tmp/%s.XXXX` %s' % (sockname,cmd))

