#!/usr/bin/env python3
# NOTE: This script depends on aiohttp.
import iterm2
from aiohttp import web
import asyncio
import re


async def main(connection):
    app = await iterm2.async_get_app(connection)

    async def send_html(txt, request):
        binary = txt.encode('utf8')
        resp = web.StreamResponse()
        resp.content_length = len(binary)
        resp.content_type = 'text/html'
        await resp.prepare(request)
        await resp.write(binary)
        return resp

    job_color = {"emacsclient": "indigo",
                 "python3": "skyblue",
                 "python3.6": "skyblue",
                 "zsh": "black",
                 "gogs": "orangered",
                 "vim": "seagreen",
                 "mysql": "red",
                 }

    tab_color_list = {"crimson": (220, 20, 60),
                      "pink": (255, 192, 203),
                      "purple": (128, 0, 128),
                      "indigo": (75, 0, 130),
                      "black": (0, 0, 0),
                      "blue": (0, 0, 255),
                      "navy": (0, 0, 128),
                      "skyblue": (135, 206, 235),
                      "orange": (255, 165, 0),
                      "orangered": (255, 69, 0),
                      "darkorange": (255, 140, 0),
                      "red": (255, 0, 0),
                      "yellow": (255, 255, 0),
                      "olive": (128, 128, 0),
                      "gold": (255, 215, 0),
                      "green": (0, 128, 0),
                      "seagreen": (46, 139, 87),
                      "springgreen": (60, 179, 113),
                      }

    async def update_tab_color_by_name(request):
        session = app.current_terminal_window.current_tab.current_session
        reader = await request.post()
        red = tab_color_list[reader["name"]][0]
        green = tab_color_list[reader["name"]][1]
        blue = tab_color_list[reader["name"]][2]
        await __update_tab_color(session, red, green, blue)
        print("__update_tab_color")  # 日志
        return await send_html("done", request)  # 返回值

    async def update_tab_color_by_rgb(request):
        session = app.current_terminal_window.current_tab.current_session
        reader = await request.post()
        red = int(reader["red"])
        green = int(reader["green"])
        blue = int(reader["blue"])
        await __update_tab_color(session, red, green, blue)
        print("__update_tab_color")  # 日志
        return await send_html("done", request)  # 返回值

    async def __update_tab_color(session, red, green, blue):
        profile = await session.async_get_profile()
        # session = app.current_terminal_window.current_tab.current_session
        # change = iterm2.LocalWriteOnlyProfile()
        change = profile
        # color = iterm2.Color(255, 128, 128)
        color = iterm2.Color(red, green, blue)
        await change.async_set_tab_color(color)
        await change.async_set_use_tab_color(True)
        # await session.async_set_profile_properties(change)

    async def __update_tab_color_by_jobname(session, jobname):
        print("---"*5)
        if jobname in job_color.keys():
            print(job_color[jobname])
            color = tab_color_list[job_color[jobname]]
            await __update_tab_color(session, color[0], color[1], color[2])


    async def __select_tab(tab_index):
        await app.current_terminal_window.tabs[tab_index].async_select()

    async def select_tab(request):
        reader = await request.post()
        await __select_tab(int(reader["tab_index"]))
        return await send_html("done", request)  # 返回值

    async def __move_tab(tab_index):
        tabs = app.current_terminal_window.tabs
        current_tab = app.current_terminal_window.current_tab
        current_tab_index = tabs.index(current_tab)
        tabs.remove(current_tab)
        if current_tab_index > tab_index:
            tabs.insert(tab_index + 1, current_tab)
        else:
            tabs.insert(tab_index, current_tab)
        await app.current_terminal_window.async_set_tabs(tabs)

    async def move_tab(request):
        reader = await request.post()
        tab_index = int(reader["tab_index"])
        await __move_tab(tab_index)
        return await send_html("done", request)  # 返回值

    async def update_path_info(request):
        reader = await request.post()
        session = app.current_terminal_window.current_tab.current_session
        if "name" in reader:
            await session.async_set_variable("user.path_info", reader["name"])
            print("update_path_info:<{}>".format(reader["name"]))  # 日志
        return await send_html("done", request)  # 返回值

    async def update_filepath(request):
        reader = await request.post()
        session = app.current_terminal_window.current_tab.current_session
        await session.async_set_variable("user.filepath", reader["filepath"])
        print("update_filepath:<{}>".format(reader["filepath"]))  # 日志
        return await send_html("done", request)  # 返回值

    async def __update_tab(session):
        tab_index = await session.async_get_variable("user.tab_index")
        jobname, path_info, filepath, tag = await __get_title_variables(session)
        title = __format_title(tab_index, path_info, filepath, tag)
        await session.tab.async_set_title(title)

    async def update_tag(request):
        reader = await request.post()
        session = app.current_terminal_window.current_tab.current_session
        await session.async_set_variable("user.tag", reader["tag"])

        await __update_tab(session)
        print("update_tag:<{}>".format(reader["tag"]))  # 日志
        return await send_html("done", request)  # 返回值



    def __format_title(tab_index, path_info, filepath, tag):
        '''
        # 中文显示出问题的原因,
        # 由于官方在用到json.dumps时没有加入参数ensure_ascii=False, 才导致的问题:
        # 调用关系: tab.py#async_set_title函数 -> util.py#invocation_string函数
        # 对官方库做的具体修改如下:
        def invocation_string(
                method_name: str, argdict: typing.Dict[str, typing.Any]) -> str:
            """Gives the invocation string for a method call with given arguments."""
            parts = []
            for name, value in argdict.items():
                parts.append(f"{name}: {json.dumps(value, ensure_ascii=False)}")  #<---(((具体修改点)))
            return method_name + "(" + ", ".join(parts) + ")"
        '''
        tag = "@{}".format(tag) if tag  else ""
        title = "{:>2}|<{}> {} |{}".format(tab_index, path_info, tag, filepath)
        return title

    async def __get_title_variables(session):
        jobname = await session.async_get_variable("jobName")

        if jobname == "zsh":
            #await session.async_set_variable("user.filepath", None)
            path = await session.async_get_variable("path")
            pathlist = path.split('/')
            full_path_list = pathlist[-1]
            #print(pathlist)
            filepath = '     /' + '/'.join([p[0] for p in pathlist[0:-1] if len(p)>0]) +'/' + full_path_list
            #filepath = ""
        else:
            filepath = await session.async_get_variable("user.filepath")

        path_info = await session.async_get_variable("user.path_info")
        tag = await session.async_get_variable("user.tag")

        # 适配
        jobname = jobname if jobname else ""
        path_info = path_info if path_info else ""
        filepath = filepath if filepath else ""
        tag = tag if tag else ""
        return jobname, path_info, filepath, tag


    async def __refresh_tab_titles_only_text():
        tabs = app.current_terminal_window.tabs
        for tab in tabs:

            for session in tab.sessions:

                tab_index = tabs.index(tab)
                jobname, path_info, filepath, tag = await __get_title_variables(session)
                await session.async_set_variable("user.tab_index", tab_index)
                title =  __format_title(tab_index, path_info, filepath, tag)
                await session.tab.async_set_title(title)

    async def __refresh_tab_titles():
        tabs = app.current_terminal_window.tabs
        for tab in tabs:

            for session in tab.sessions:

                tab_index = tabs.index(tab)
                jobname, path_info, filepath, tag = await __get_title_variables(session)
                await session.async_set_variable("user.tab_index", tab_index)

                color_jobname = ""
                if jobname in job_color.keys():
                    color_jobname = job_color[jobname]
                    color = tab_color_list[color_jobname]
                    await __update_tab_color(session, color[0], color[1], color[2])

                title =  __format_title(tab_index, path_info, filepath, tag)
                await session.tab.async_set_title(title)

                # 打印信息
                print("{}:{}:{}".format(tab_index, jobname, color_jobname))

    async def refresh_tab_titles(request):
        print("refresh_tab_titles")
        await __refresh_tab_titles()
        # for window in app.terminal_windows:
        return await send_html("done", request)  # 返回值

    async def refresh_tab_titles_only_text(request):
        print("refresh_tab_titles")
        await __refresh_tab_titles_only_text()
        # for window in app.terminal_windows:
        return await send_html("done", request)  # 返回值


    def __sort_tab_strategy(tab):
        """
        排序规则
        """
        return tab.sort_strategy if tab.sort_strategy else ""

    async def __sort_tabs(sort_strategy, variable):
        for window in app.terminal_windows:
            tabs = window.tabs
            for tab in tabs:
                session = tab.sessions[0]
                tab.sort_strategy = await session.async_get_variable(variable)
            sorted_tabs = sorted(tabs, key=sort_strategy)
            sorted_tabs.reverse()
            await window.async_set_tabs(sorted_tabs)

    async def sort_tabs(request):
        print("sort_tabs")
        await  __sort_tabs(__sort_tab_strategy, "user.path_info")
        return await send_html("done", request)  # 返回值

    async def sort_tabs_by_job(request):
        print("sort_tabs")
        await  __sort_tabs(__sort_tab_strategy, "jobName")
        return await send_html("done", request)  # 返回值

    async def sort_tabs_by_tag(request):
        print("sort_tabs")
        await  __sort_tabs(__sort_tab_strategy, "user.tag")
        return await send_html("done", request)  # 返回值

    async def __update_tab_for_search(session):
        tab_index = await session.async_get_variable("user.tab_index")
        jobname, path_info, filepath, tag = await __get_title_variables(session)
        path_info = "{}|{}".format(path_info, jobname)
        title = __format_title(tab_index, path_info, filepath, tag)
        await session.tab.async_set_title(title)

    async def sort_tabs_by_search(request):
        print("working")
        reader = await request.post()
        search = reader["search"]
        print(search)
        tabs = []
        for window in app.terminal_windows:
            tabs = window.tabs
        tabs_searched = [ tab for tab in tabs if re.search(search, await tab.async_get_variable("title"))]
        if len(tabs_searched) == 0:
          return await send_html("done", request)  # 返回值

        for tab in tabs_searched:
            await __update_tab_color(
                tab.current_session,
                red=tab_color_list["gold"][0],
                green=tab_color_list["gold"][1],
                blue=tab_color_list["gold"][2],
            )
            await __update_tab_for_search(tab.current_session)
            tabs.remove(tab)

        tabs = tabs_searched + tabs
        await window.async_set_tabs(tabs)

        return await send_html("done", request)  # 返回值

    async def search_or_goto(request):
        reader = await request.post()
        search_or_goto = reader["search_or_goto"]
        if re.match(r'\d+', search_or_goto):
            await __select_tab(int(search_or_goto))
            #await search(search_or_goto)
        else:
            await __search(search_or_goto)

        return await send_html("done", request)  # 返回值

   
    async def __search(search):
        tabs = []
        for window in app.terminal_windows:
            tabs = window.tabs
        tabs_searched = [ tab for tab in tabs if re.search(search, await tab.async_get_variable("title"))]
        if len(tabs_searched) == 0:
          return await send_html("done", request)  # 返回值

        for tab in tabs_searched:
            await __update_tab_color(
                tab.current_session,
                red=tab_color_list["gold"][0],
                green=tab_color_list["gold"][1],
                blue=tab_color_list["gold"][2],
            )


    async def search(request):
        print("search")
        reader = await request.post()
        search = reader["search"]
        print(search)
        await __search(search)

        #tabs = tabs_searched + tabs
        #await window.async_set_tabs(tabs)

        return await send_html("done", request)  # 返回值


    # Set up a web server on port 9999. The web pages give the script a user interface.
    webapp = web.Application()

    # post请求默认是json, 加了-f即--form就变成了传统参数
    # http -f POST 127.0.0.1:9999/__update_tab_color red=255 green=100 blue=23
    webapp.router.add_post('/update_tab_color_by_rgb', update_tab_color_by_rgb)
    webapp.router.add_post('/update_tab_color_by_name', update_tab_color_by_name)
    webapp.router.add_post('/select_tab', select_tab)
    webapp.router.add_post('/search_or_goto', search_or_goto)
    
    webapp.router.add_post('/move_tab', move_tab)
    webapp.router.add_post('/sort_tabs', sort_tabs)
    webapp.router.add_post('/sort_tabs_by_job', sort_tabs_by_job)
    webapp.router.add_post('/sort_tabs_by_tag', sort_tabs_by_tag)
    webapp.router.add_post('/sort_tabs_by_search',  sort_tabs_by_search)
    webapp.router.add_post('/update_path_info', update_path_info)
    webapp.router.add_post('/update_filepath', update_filepath)
    webapp.router.add_post('/update_tag', update_tag)
    webapp.router.add_post('/refresh_tab_titles', refresh_tab_titles)
    webapp.router.add_post('/refresh_tab_titles_only_text', refresh_tab_titles_only_text)
    webapp.router.add_post('/search', search)

    # webapp.router.add_post('/refresh_tab_titles', refresh_tab_titles)

    runner = web.AppRunner(webapp)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', 9999)
    await site.start()  # 服务器启动

    # 事件中心 (((暂时用不到)))
    async def monitor(session_id):
        """Run for each session, including existing sessions. Watches for
        changes to the running commands."""
        session = app.get_session_by_id(session_id)
        if not session:
            return
        alert_task = None
        modes = [iterm2.PromptMonitor.Mode.COMMAND_END,
                 iterm2.PromptMonitor.Mode.PROMPT,
                 iterm2.PromptMonitor.Mode.COMMAND_START]
        #modes = list(range(10))
        async with iterm2.PromptMonitor(
                connection, session_id, modes=modes) as mon:
            while True:
                try:  #注意这里如果要调试要加个try, 不然可能被上面的with把错误吃掉而看不到
                  mode, _ = await mon.async_get()
                  print("monitor")

                  await asyncio.sleep(1)
                  if session.window and session.window.tabs and session.tab in session.window.tabs:
                      tab_index = session.window.tabs.index(session.tab)
                      await session.async_set_variable("user.tab_index", tab_index)
                  else:
                    tab_index = "-1"
                    #app.current_terminal_window.tabs #在封闭的mon环境中, 直接访问app似乎有问题,建议间接
                    #app.current_tab #在封闭的mon环境中, 直接访问app似乎有问题,建议间接
                  jobname, path_info, filepath, tag = await __get_title_variables(session)
                  title =  __format_title(tab_index, path_info, filepath, tag)
                  await session.tab.async_set_title(title)
                  await __update_tab_color_by_jobname(session, jobname)
                except Exception as e:
                  print("!!!Exception!!!: {}", e)
                  print('文件', e.__traceback__.tb_frame.f_globals['__file__'])
                  print('行号', e.__traceback__.tb_lineno)

        print("mointor quit")



    await iterm2.EachSessionOnceMonitor.async_foreach_session_create_task(
        app, monitor)


iterm2.run_forever(main)
