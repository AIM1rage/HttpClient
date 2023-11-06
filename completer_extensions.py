from prompt_toolkit.completion import WordCompleter, Completion


class SingleWordCompleter(WordCompleter):
    def __init__(self, words):
        super().__init__(words)

    def get_completions(self, document, complete_event):
        input_text = document.text.lower()
        if " " not in input_text:
            for word in self.words:
                if word.lower().startswith(input_text):
                    yield Completion(word, start_position=-len(input_text))
