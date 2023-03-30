# Chat-team

## what is this

did you ever wondering what would happen when get more than one gpt chatbot in one place?
I am wondering too ,so I make this.

这个GitHub项目是一个有趣的实验，它允许您在同一聊天组中放置多个AI，观察它们在互动中的反应。

expect your story

期待见到你的剧本

## demos

such as

甜咸之争: 让两个ai争论甜咸豆腐脑的问题

Let two opposing AI argue about sweet versus salty

![甜咸之争](demos/sweet%20versus%20salty.gif)

ai主持开发会议: 让ai主持一个开发会议,来解决一个问题,他们共享上下文,知道彼此的发言

Let an AI host a development meeting, with other AI participants that are aware of each other's existence.

![ai主持开发会议](demos/ai%20holder.png)

用户主持开发会议: 你自己@人来让他们解决问题,他们共享上下文,知道彼此的发言

It's you hosting that development meeting

![用户主持开发会议](demos/user%20holder.png)

并发男友: 对多个prompt同时进行提问

Different prompts answering your questions simultaneously.

![并发男友](demos/concurrent%20boyfriend.png)

## get start

clone repo

```
git clone https://github.com/tyrickareo/chat-team.git
```

pip install

```
pip install -r requirements.txt

```

set up openai api key

```
setting.py

openai.api_key = "<YOUR API KEY>"
```

run

```
python main.py
```

visit
[http://localhost:8000](http://localhost:8000)

## strategy

围绕如何驱动ai进行聊天而产生的方法叫做策略

those above demos are all different strategies, you can choose one of them to make your chat-team story.

目前实现的策略有:
 - ai主持人: 选定一个主持人让他决定下一个谁来发言
 - 用户主持: 你自己@人来让他们进行发言
 - 击鼓传花: 轮流发言
 - 简单并发: 同时回答你的提问

## Roadmap

### more strategy

    - [√] ai holder
    - [√] round
    - [√] concurrency
    - [√] user hold
    - [x] random
    - [x] vote
    - [x] hot potato

### persistence

    - [x] sqllite
    - [x] loclafile

### language

    - [√] chinese
    - [x] english

### wait for gpt4
    - a longer context will be much more helpful

