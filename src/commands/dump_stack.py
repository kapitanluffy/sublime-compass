from ..stack import STACK
import sublime
import sublime_plugin


class CompassDumpStackCommand(sublime_plugin.WindowCommand):
    def run(self):
        window_stack = list(filter(lambda block: block[0] == self.window.id(), STACK))
        print("STACK>")
        for item in window_stack:
            for sheet in item[2]:
                s = sublime.Sheet(sheet)
                v = s.view()
                name = v.name() if v is not None else None
                print("\t%s: %s" % (s.id(), s.file_name() or name or "Untitled #%s" % s.id()))
        print("ENDSTACK>")
