import json
import pathlib

import gradio as gr

from service.holder import ChatMessage, User, Holder, AIHolder, Bot, ChatMessageList, UserHolder, RoundRobin, Switch, \
    Random
from service.llm import test_connection


def init_switch(meeting, progress):
    participants = meeting["participants"]
    meeting_prompt = meeting["meeting_prompt"]
    me = meeting["who_am_i"]
    readme = meeting["readme"]

    msg_list = ChatMessageList()
    user = User(name=me["name"], title=me["title"], prompt=me["prompt"])

    switch = Switch(user=user, msg_list=msg_list)
    switch.share_msg_with(user)
    the_holder = Holder.new_meeting(
        switch, about=meeting["objective"])

    for p in participants:
        participants[p]["prompt"] = f"{participants[p]['prompt']}\n{meeting_prompt}"
        ml = ChatMessageList()
        bot = Bot(**participants[p], msg_list=ml)
        the_holder.add_participant(bot)

    progress(0.4)
    the_holder.holder_note.append(dict(event="meeting_started", result=test_connection()))
    progress(0.8)
    return the_holder, user, gr.update(label=the_holder.meeting_about, visible=True), "\n".join(
        [f"{p}({participants[p]['title']})" for p in participants]) + "\n\n\n-------------------\n" + readme


def init_random(meeting, progress):
    participants = meeting["participants"]
    meeting_prompt = meeting["meeting_prompt"]
    me = meeting["who_am_i"]
    readme = meeting["readme"]
    factor = meeting["strategy"]["factor"]
    random_plot = meeting["strategy"]["random_plot"]

    msg_list = ChatMessageList()
    user = User(name=me["name"], title=me["title"], prompt=me["prompt"])

    random = Random(user=user, msg_list=msg_list, factor=factor, random_plot=random_plot)
    random.share_msg_with(user)
    the_holder = Holder.new_meeting(
        random, about=meeting["objective"])

    for p in participants:
        participants[p]["prompt"] = f"{participants[p]['prompt']}\n{meeting_prompt}"
        bot = Bot(**participants[p])
        random.share_msg_with(bot)
        the_holder.add_participant(bot)

    progress(0.4)
    the_holder.holder_note.append(dict(event="meeting_started", result=test_connection()))
    progress(0.8)
    return the_holder, user, gr.update(label=the_holder.meeting_about, visible=True), "\n".join(
        [f"{p}({participants[p]['title']})" for p in participants]) + "\n\n\n-------------------\n" + readme


def init_round_robin(meeting, progress):
    participants = meeting["participants"]
    meeting_prompt = meeting["meeting_prompt"]
    me = meeting["who_am_i"]
    readme = meeting["readme"]

    sequence = meeting["sequence"]
    default_seq = list(participants.keys())
    if sequence:
        default_seq = sequence
    msg_list = ChatMessageList()
    robin = RoundRobin(sequence=default_seq, msg_list=msg_list)
    the_holder = Holder.new_meeting(
        robin, about=meeting["objective"])
    user = User(name=me["name"], title=me["title"], prompt=me["prompt"])
    robin.share_msg_with(user)
    for p in participants:
        participants[p]["prompt"] = f"{participants[p]['prompt']}\n{meeting_prompt}"
        bot = Bot(**participants[p])
        robin.share_msg_with(bot)
        the_holder.add_participant(bot)
    progress(0.4)
    the_holder.holder_note.append(dict(event="meeting_started", result=test_connection()))
    progress(0.8)
    return the_holder, user, gr.update(label=the_holder.meeting_about, visible=True), "\n".join(
        [f"{p}({participants[p]['title']})" for p in participants]) + "\n\n\n-------------------\n" + readme


def init_ai_holder_meeting(meeting, progress):
    holder = meeting["strategy"]["holder"]
    participants = meeting["participants"]
    meeting_prompt = meeting["meeting_prompt"]
    readme = meeting["readme"]

    if type(holder) == str:
        holder_bot = Bot(**participants[holder])
    else:
        holder_bot = Bot(**holder)
    holder_bot.prompt = f"{holder_bot.prompt}\n{meeting_prompt}"
    msg_list = ChatMessageList()
    ai_holder = AIHolder(msg_list=msg_list, holder=holder_bot, choice_prompt=meeting["strategy"]["choice_prompt"])
    the_holder = Holder.new_meeting(
        ai_holder, about=meeting["objective"])
    ai_holder.share_msg_with(holder_bot)
    me = meeting["who_am_i"]
    user = User(name=me["name"], title=me["title"], prompt=me["prompt"])
    ai_holder.share_msg_with(user)
    the_holder.add_participant(user)

    for p in participants:
        participants[p]["prompt"] = f"{participants[p]['prompt']}\n{meeting_prompt}"
        bot = Bot(**participants[p])
        ai_holder.share_msg_with(bot)
        the_holder.add_participant(bot)
    progress(0.4)
    the_holder.holder_note.append(dict(event="meeting_started", result=test_connection()))
    progress(0.8)
    return the_holder, user, gr.update(label=the_holder.meeting_about, visible=True), "\n".join(
        [f"{p}({participants[p]['title']})" for p in participants]) + "\n\n\n-------------------\n" + readme


def init_user_holder_meeting(meeting, progress):
    participants = meeting["participants"]
    meeting_prompt = meeting["meeting_prompt"]
    me = meeting["who_am_i"]
    readme = meeting["readme"]
    user = User(name=me["name"], title=me["title"], prompt=me["prompt"])

    msg_list = ChatMessageList()
    user_holder = UserHolder(msg_list=msg_list, holder=user)
    the_holder = Holder.new_meeting(user_holder, about=meeting["objective"])
    user_holder.share_msg_with(user)

    for p in participants:
        participants[p]["prompt"] = f"{participants[p]['prompt']}\n{meeting_prompt}"
        bot = Bot(**participants[p])
        user_holder.share_msg_with(bot)
        the_holder.add_participant(bot)
    progress(0.4)
    the_holder.holder_note.append(dict(event="meeting_started", result=test_connection()))
    progress(0.8)
    return the_holder, user, gr.update(label=the_holder.meeting_about, visible=True), "\n".join(
        [f"{p}({participants[p]['title']})" for p in participants]) + "\n\n\n-------------------\n" + readme


def create_meeting(meeting_name, meeting_setting, room, progress=gr.Progress()):
    if not meeting_setting:
        raise gr.Error("请先从下面选择一个会议")

    meeting_setting = json.loads(meeting_setting)
    selected_meeting = meeting_setting["meeting"][meeting_name]
    progress(0.1)
    match selected_meeting["strategy"]["type"]:
        case "aiholder" | "AIHolder" | "ai主持":
            holder, user, about, parti = init_ai_holder_meeting(selected_meeting, progress)
            return holder, user, about, parti, True, gr.update(value="会议已开始", interactive=False), room, [
                (None, holder.desc_meeting())], gr.update(placeholder="enter text", interactive=True)
        case "userholder" | "UserHolder" | "用户主持":
            holder, user, about, parti = init_user_holder_meeting(selected_meeting, progress)
            return holder, user, about, parti, True, gr.update(value="会议已开始", interactive=False), room, [
                (None, holder.desc_meeting())], gr.update(placeholder="enter text", interactive=True)
        case "roundrobin" | "RoundRobin" | "击鼓传花":
            holder, user, about, parti = init_round_robin(selected_meeting, progress)
            return holder, user, about, parti, True, gr.update(value="会议已开始", interactive=False), room, [
                (None, holder.desc_meeting())], gr.update(placeholder="enter text", interactive=True)
        case "switch" | "Switch" | "简单并发":
            holder, user, about, parti = init_switch(selected_meeting, progress)
            return holder, user, about, parti, True, gr.update(value="会议已开始", interactive=False), room, [
                (None, holder.desc_meeting())], gr.update(placeholder="enter text", interactive=True)
        case "random" | "Random" | "随机":
            holder, user, about, parti = init_random(selected_meeting, progress)
            return holder, user, about, parti, True, gr.update(value="会议已开始", interactive=False), room, [
                (None, holder.desc_meeting())], gr.update(placeholder="enter text", interactive=True)
        case _:
            raise ValueError("no such strategy")


def add_text(holder, user, text):
    holder.input(ChatMessage(user_name=user.name, supplement=user.title, content=text))
    return user.view(), "", gr.update(visible=False), gr.update(visible=True), gr.update(
        visible=True)


def after_bot():
    return gr.update(visible=True), gr.update(visible=False), gr.update(visible=False)


def on_chatbot_answer(holder, user, history):
    for lines in holder.starts():
        # cache this
        history = user.view()
        for msg in lines:
            history.append((None, f"{msg[0]}: {msg[1]}"))
        yield history

    yield user.view()


def wait_btn_click(state):
    return gr.update(visible=state), not state


def send_btn_click(state):
    return gr.update(visible=not state), not state


with gr.Blocks(title="About what", css="./asset/style.css", theme=gr.themes.Monochrome()) as chat_team_app:
    waiting = gr.State(False)
    meeting_holder = gr.State(None)  # may run into a race contition due to multi-threading
    user_p = gr.State(None)  # may run into a race contition due to multi-threading
    my_preset = json.loads(pathlib.Path("./asset/preset.json").read_text(encoding="utf-8"))
    cfg = gr.State(json.dumps(my_preset, indent=4, ensure_ascii=False))

    with gr.Row():
        with gr.Column(scale=6):
            chatbot = gr.Chatbot([], elem_id="chatbot-msg-box")
            with gr.Row():
                with gr.Column(scale=85):
                    user_input = gr.Textbox(
                        show_label=False,
                        placeholder="start meeting first",
                        interactive=False
                    ).style(container=False)
                with gr.Column(scale=15, min_width=200):
                    with gr.Row():
                        with gr.Column(scale=5, min_width=50, visible=False) as col1:
                            hand_up = gr.Button("举手")
                        with gr.Column(scale=5, min_width=50, visible=False) as col2:
                            cancel = gr.Button("停止")
                        send = gr.Button("发送")

            hello = gr.State(False)


            def on_hand_up(holder):
                holder.user_raised_hand()


            def on_cancel(holder):
                holder.user_cancel()

        meeting_started = gr.State(False)

        with gr.Column(scale=4):
            with gr.Row(elem_id="setting-panel"):
                with gr.Tab("会议室"):
                    selected_room = gr.Text(label="当前会议", interactive=False)
                    exp = gr.Examples(examples=my_preset["room"], label="可选会议", inputs=selected_room)
                    start_meeting_btn = gr.Button("开始会议")
                    participant = gr.TextArea(lines=10, visible=False)

                with gr.Tab("会议配置"):
                    meeting_config = gr.TextArea(label="会议配置",
                                                 value=cfg.value,
                                                 interactive=True, lines=30)

                with gr.Tab("设置"):
                    # gr.Textbox(label="api-key")
                    # gr.Dropdown(["en", "中文"], label="语言")
                    ...
                with gr.Tab("事件"):
                    logs = gr.Markdown(label="事件", interactive=False)

        start_meeting_btn.click(create_meeting, [selected_room, meeting_config, selected_room],
                                [meeting_holder, user_p, participant, participant, meeting_started, start_meeting_btn,
                                 selected_room,
                                 chatbot,
                                 user_input]).then(
            lambda x: x.to_display_log(), [meeting_holder], [logs], every=0.5)

        user_input.submit(add_text, [meeting_holder, user_p, user_input], [chatbot, user_input, send, col1, col2]) \
            .then(on_chatbot_answer, [meeting_holder, user_p, chatbot], [chatbot]) \
            .then(after_bot, [], [send, col1, col2])
        send.click(add_text, [meeting_holder, user_p, user_input], [chatbot, user_input, send, col1, col2]) \
            .then(on_chatbot_answer, [meeting_holder, user_p, chatbot], [chatbot]) \
            .then(after_bot, [], [send, col1, col2])

        hand_up.click(on_hand_up, [meeting_holder], [])
        cancel.click(on_cancel, [meeting_holder], [])
chat_team_app.queue(concurrency_count=100).launch(server_port=8000, server_name="0.0.0.0")
