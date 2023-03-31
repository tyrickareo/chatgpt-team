import json
import random
import re
import time
from typing import List, Dict, Tuple

from pydantic import BaseModel

from .llm import get_whole_response, Message, get_char_stream, get_stream_from_openai


class ChatMessage(BaseModel):
    user_name: str | None
    content: str | None
    supplement: str | None
    user_invisible: bool = False
    bot_invisible: bool = False


def ChatMessageList():
    msg_list: List[ChatMessage] = []

    def push_message(msg: ChatMessage):
        msg_list.append(msg)

    def copy(x):
        return x

    def get_msg_list(map_=copy, index=None):
        if index is not None:
            return msg_list[index]
        result = []
        for m in msg_list:
            r = map_(m)
            if r is None:
                continue
            result.append(r)
        return result

    return get_msg_list, push_message


class Participant(BaseModel):
    title: str | None
    name: str
    prompt: str | None
    msg_list: Tuple | None

    class Config:
        copy_on_model_validation = 'none'

    def view(self) -> List[ChatMessage | Message]:
        pass

    def answer(self):
        raise NotImplementedError

    def desc(self):
        return ""


class MeetingError(BaseException):
    pass


class UserCancel(MeetingError):
    pass


class UserTurnInterrupt(MeetingError):
    pass


class Bot(Participant):
    instruction: str = ""

    def view_(self):
        result = []
        temp = []
        msg_list = self.msg_list[0]()
        for i, msg in enumerate(msg_list[::-1]):
            if msg.user_name == self.name:
                if temp:
                    compress = "\n\n".join([f"{m.user_name}: ({m.content})" for m in temp[::-1]])
                    result.append(Message(role="user", content=compress))
                    temp = []
                result.append(Message(role="assistant", content=msg.content))
                continue
            temp.append(msg)
        else:
            if temp:
                compress = "\n\n".join([f"{m.user_name}: ({m.content})" for m in temp[::-1]])
                result.append(Message(role="user", content=compress))
        result.append(Message(role="system", content=self.prompt))
        return result[::-1]

    def map_(self, msg: ChatMessage):
        if msg.bot_invisible:
            return None
        if msg.user_name == self.name:
            return Message(role="assistant", content=msg.content)
        return Message(role="user", content=f"{msg.user_name}: {msg.content}")

    def view(self):
        result = self.msg_list[0](self.map_)
        result.insert(0, Message(role="system", content=self.prompt))
        return result

    def answer(self):
        reorganize = self.view()
        content = reorganize[-1].content + "\n\n" + self.instruction
        reorganize[-1].content = content
        return get_char_stream(get_stream_from_openai(reorganize))

    def desc(self):
        return f"{self.name} is answering"


class User(Participant):

    def answer(self):
        raise UserTurnInterrupt

    def view(self):
        return self.msg_list[0](
            lambda x: None if x.user_invisible else (x.content, None) if x.user_name == self.name else (
                None, f"{x.user_name}: {x.content}"))

    def desc(self):
        return "waiting for user input"


class Troublemaker(Participant):
    ...


class Strategy(BaseModel):
    name = ""
    participants: Dict[str, Participant] = {}
    msg_list: Tuple

    def next(self, *args, **kwargs) -> List[Tuple[Participant, str]]:
        raise NotImplementedError

    def solid(self, *args, **kwargs) -> ChatMessage | None:
        raise NotImplementedError

    def desc_this_meeting(self):
        return ""

    def share_msg_with(self, p: Participant):
        p.msg_list = self.msg_list

    def input(self, msg: ChatMessage):
        raise NotImplementedError


class AIHolder(Strategy):
    name = "AIHolder"
    holder: Bot
    choice_prompt: str

    __choice_prompt_desc__ = """
    #### you should ask ai answer in this json format:
    
    ```json
    {"next":"<participant>","reason";"<some reasons>"}
    ```
    
    #### allow variables:
        - /PARTICIPANTS/ : all participant names in comma separated
    """

    def reorganize(self) -> List[Message]:
        return self.holder.view()

    def next(self) -> List[Tuple[Participant, str]]:
        reorganized_msgs = self.reorganize()

        content = reorganized_msgs[-1].content

        PARTICIPANTS = ",".join(self.participants)

        q = self.choice_prompt.replace("/PARTICIPANTS/", PARTICIPANTS)
        reorganized_msgs[-1].content = content + "\n\n" + q + "\n\n" + self.holder.instruction
        response = get_whole_response(reorganized_msgs)
        print("decision: ", response)
        # some retry things
        try:
            loads = json.loads(response)
            name, reason, question = loads["next"], loads["reason"], loads["question"]

        except json.JSONDecodeError:
            emphasis = '"所有的回答请写在下面的json格式里,就像这样:\n-----\n{\"next\":\"玛丽\",\"reason\":\"我觉得他会推进我们现在的进度\",\"question\":\"请问玛丽,你觉得我们该如何做才能完成既定的目标?\"}"'
            reorganized_msgs[-1].content += emphasis
            response = get_whole_response(reorganized_msgs)
            print("llm escaped the answer format,got retry. ", response)
            loads = json.loads(response)
            name, reason, question = loads["next"], loads["reason"], loads["question"]

        self.solid(self.participants[name], reason, question)
        return [(self.participants[name], reason)]

    def solid(self, participant, reason, question):
        msg = f"@{participant.name},{question}"
        self.input(ChatMessage(user_name=self.holder.name, supplement=participant.title, content=msg))

    def desc_this_meeting(self):
        keys = self.participants.keys()
        return f"there are {len(keys)} people {','.join(keys)} in the room, and {self.holder.name} is holding the meeting"

    def input(self, msg: ChatMessage):
        self.msg_list[1](msg)


class UserHolder(AIHolder):
    name = "UserHolder"
    choice_prompt = ""

    def next(self) -> List[Tuple[Participant, str]]:
        msg = self.msg_list[0](index=-1)
        if msg.user_name != self.holder.name:
            raise UserTurnInterrupt
        strip = msg.content.strip()
        pattern = re.compile(r'@(\w+)')
        match = pattern.match(strip)
        if match:
            name = match.group(1)
        else:
            # msg.bot_invisible = True
            raise ValueError("you don't mention anyone")

        if name not in self.participants:
            # msg.bot_invisible = True
            raise ValueError(f"no such participant {name}")

        return [(self.participants[name], "user choice")]

    def desc_this_meeting(self):
        keys = self.participants.keys()
        return f"there are {len(keys)} people {','.join(keys)} in the room, and you are about to hold a meeting"


class RoundRobin(Strategy):
    name = "RoundRobin"
    sequence: List[str]
    current: str | None
    score = [0, 0]

    def next(self) -> List[Tuple[Participant, str]]:
        # if self.current is None:
        #     self.current = self.sequence[0]
        # else:
        #     self.current = self.sequence[(self.sequence.index(self.current) + 1) % len(self.sequence)]
        # return [(self.participants[self.current], "round robin")]

        if self.current is None:
            self.current = self.sequence[0]
        else:
            if self.current == "judge":
                last = self.msg_list[0](index=-1)
                if last.user_name not in self.participants:
                    if last.content.strip() == "0":
                        self.current = self.sequence[(self.sequence.index(self.current) + 1) % len(self.sequence)]
                        return [(self.participants[self.current], "round robin")]
                    pattern = re.compile(r'(\d+),(\d+)')
                    search = pattern.search(last.content)
                    if search and search.group(1) and search.group(2):
                        self.score = [self.score[0] + int(search.group(1)), self.score[1] + int(search.group(2))]
                        if self.score[0] >= 100:
                            self.input(ChatMessage(user_name="judge", supplement="judge",
                                                   content=f"game over, {self.sequence[0]} win"))
                            raise UserTurnInterrupt
                        if self.score[1] >= 100:
                            self.input(ChatMessage(user_name="judge", supplement="judge",
                                                   content=f"game over, {self.sequence[1]} win"))
                            raise UserTurnInterrupt

                        self.input(ChatMessage(user_name="judge", supplement="judge",
                                               content=f"目前得分为{self.sequence[0]}:{self.score[0]}, {self.sequence[1]}:{self.score[1]}"))
                    else:
                        print("judge ignored, because of wrong format,", last.content)

            self.current = self.sequence[(self.sequence.index(self.current) + 1) % len(self.sequence)]

            if self.current == "judge":
                self.input(ChatMessage(user_name="judge", supplement="judge",
                                       content="请裁判评分,按照顺序输入两个数字,第一个数字为第一个人的分数,第二个数字为第二个人的分数,用逗号隔开",
                                       bot_invisible=True))
                raise UserTurnInterrupt

        return [(self.participants[self.current], "round robin")]

    def desc_this_meeting(self):
        keys = self.participants.keys()
        return f"there are {len(keys)} people {','.join(keys)} in the room, and people speak in order, one after another"

    def input(self, msg: ChatMessage):
        if msg.user_name not in self.participants:
            if msg.user_name != "judge":
                if msg.content.strip() == "0":
                    msg.bot_invisible = True

                pattern = re.compile(r'(\d+),(\d+)')
                search = pattern.search(msg.content)
                if search and search.group(1) and search.group(2):
                    msg.bot_invisible = True

        self.msg_list[1](msg)


class Switch(Strategy):
    name = "Switch"
    user: User

    def next(self, *args, **kwargs) -> List[Tuple[Participant, str]]:
        last = self.msg_list[0](index=-1)
        if last.user_name != self.user.name:
            raise UserTurnInterrupt
        return [(p, "switch") for p in self.participants.values()]

    def input(self, msg: ChatMessage):
        if msg.user_name == self.user.name:
            self.msg_list[1](msg)
            for p in self.participants.values():
                p.msg_list[1](msg)
        else:
            self.msg_list[1](msg)
            self.participants[msg.user_name].msg_list[1](msg)

    def desc_this_meeting(self):
        return "all the bots speak at the same time"


class Random(Strategy):
    name = "Random"

    # factor=0 means just one speak. factor > 0 means at least one speak. factor=1 means everyone speak
    factor: float = 0.2
    random_plot: bool = False

    def next(self, *args, **kwargs) -> List[Tuple[Participant, str]]:
        if not self.random_plot:
            last = self.msg_list[0](index=-1)
            if last.user_name in self.participants:
                raise UserTurnInterrupt
        result = [(p, "random") for p in self.participants.values() if random.random() < self.factor]
        if not result:
            result.append((random.choice(list(self.participants.values())), "random"))
        return result

    def desc_this_meeting(self):
        return "randomly select one bot to speak"

    def input(self, msg: ChatMessage):
        self.msg_list[1](msg)


class Holder(BaseModel):
    holder_note: List[Dict]
    strategy: Strategy
    next: List[Participant] | None
    user_signal: int = 0
    status_desc: str = ""
    breathing: int = 5
    meeting_about: str = ""

    def desc_meeting(self):
        return f"meeting about {self.meeting_about}." + self.strategy.desc_this_meeting()

    def whats_happening(self):
        return self.status_desc

    def decide_which_next(self):
        point = time.time()
        self.status_desc = "deciding next"
        pairs = self.strategy.next()
        next_tick = []
        for p, r in pairs:
            self.holder_note.append(dict(event=self.strategy.name, result=f"{p.name} is next, reason: {r}"))
            next_tick.append(p)
        self.next = next_tick
        if (b := self.breathing - (time.time() - point)) > 0 and not isinstance(self.next, User):
            # await anyio.sleep(b)
            ...
        result = None
        self.status_desc = f'{",".join([p.name for p in self.next])} is answering'
        for line in self.parallel():
            if self.user_signal & 1 == 1:
                self.holder_note.append(dict(event="user cancel", result="sure"))
                self.status_desc = "user cancel"
                print("user cancel")
                self.user_signal &= 0b10
                raise UserCancel
            result = line
            yield result
        for line in result:
            self.strategy.input(ChatMessage(user_name=line[0], supplement="", content=line[1]))

        yield {}
        if self.user_signal & 2 == 2:
            self.holder_note.append(dict(event="user hand up", result="ok, you are next"))
            self.status_desc = "user hand up"
            print("user hand up")
            self.user_signal &= 0b01
            raise UserTurnInterrupt

    def input(self, msg: ChatMessage):
        self.strategy.input(msg)

    def starts(self):
        while True:
            try:
                yield from self.decide_which_next()
            except (UserTurnInterrupt, UserCancel):
                self.status_desc = "waiting for user input"
                print("user turn")
                return

    def parallel(self):
        ass = [(p.name, p.answer()) for p in self.next]
        word_lines = [("", "")] * len(ass)
        mark = {p.name for p in self.next}
        while mark:
            for i, k in enumerate(ass):
                try:
                    word = next(k[1])
                    word_lines[i] = (k[0], word_lines[i][1] + word)
                except StopIteration:
                    mark.discard(k[0])
            yield word_lines

    def user_raised_hand(self):
        self.user_signal |= 2

    def user_cancel(self):
        self.user_signal |= 1

    def to_display_log(self):
        return "\n\n".join(
            map(lambda x: f"--> {x['event']}: {x['result']}", self.holder_note)) + "\n\n" + self.whats_happening()

    def add_participant(self, p: Participant):
        self.strategy.participants[p.name] = p

    @classmethod
    def new_meeting(cls, strategy: Strategy, about: str):
        holder_note: List[Dict] = []
        return cls(holder_note=holder_note, strategy=strategy, meeting_about=about)

    # convert this to a context manager
