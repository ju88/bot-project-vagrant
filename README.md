にせBotをvagrantでうごかすやつ
===
---

Vagrant, fabricそれなりに新しいやつ

source/に bot-projectをcloneして入れてね。

```
$ cd source/
$ git clone ...
```

bot設定ファイルを編集してね。

```
$ cd bot-project/nise_bot/inc
$ cp mybot1.json nise_xxxx.json
$ vi nise_xxxx.json
...
```

db設定ファイルを編集してね。

```
$ vi config/db.json
...
```

shell設定ファイルを編集してね。

```
$ vi shell/define.sh
...
```

必要ならVagrantfile編集してから、起動してね。

```
$ vi Vagrantfile
...

$ vagrant up
```

