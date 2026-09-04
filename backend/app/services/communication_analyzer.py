"""
ReflectAI Communication Analyzer

Part 1

Responsible for extracting communication behaviour
WITHOUT using an LLM.

This file focuses on HOW the user writes.

Later, analyzer.py will combine this output
with Ollama personality analysis.
"""

from __future__ import annotations

import re
import string

from collections import Counter
from statistics import mean

import emoji


class CommunicationAnalyzer:

    def __init__(self):

        # ------------------------------------------------
        # Common internet short forms
        # ------------------------------------------------

        self.short_forms = {

            "idk",
            "imo",
            "imho",
            "irl",
            "brb",
            "btw",
            "fr",
            "frfr",
            "ngl",
            "wtf",
            "lol",
            "lmao",
            "rofl",
            "afaik",
            "ikr",
            "smh",
            "tbh",
            "rn",
            "asap",
            "fyi",
            "omg",
            "wyd",
            "wym",
            "bc",
            "cuz",
            "coz",
            "pls",
            "plz",
            "tho",
            "u",
            "ur",
            "ya",
            "nah",
            "yup"
        }

        # ------------------------------------------------
        # Fillers
        # ------------------------------------------------

        self.fillers = {

            "actually",

            "basically",

            "literally",

            "like",

            "you know",

            "i mean",

            "kind of",

            "sort of",

            "well",

            "okay",

            "bro",

            "dude",

            "man"
        }

        # ------------------------------------------------
        # Curse words
        # ------------------------------------------------

        self.curse_words = {

            "fuck",

            "fucking",

            "shit",

            "damn",

            "hell",

            "bitch",

            "ass",

            "wtf"
        }

        # ------------------------------------------------
        # Stop words

        # We keep this intentionally tiny because
        # words like "bro" are important.
        # ------------------------------------------------

        self.stop_words = {

            "a",

            "an",

            "the",

            "is",

            "are",

            "am",

            "was",

            "were",

            "to",

            "of",

            "in",

            "on",

            "at",

            "for",

            "and",

            "or",

            "but"
        }

    # =======================================================
    # Main API
    # =======================================================
    def analyze(self, messages):

        text = self.combine_messages(messages)

        tokens = self.tokenize(text)

        communication = self.communication_fingerprint(

            text,

            tokens,

            messages

        )

        return communication

    def combine_messages(self, messages):
        """
        Combine all user messages into a single text block for
        communication analysis.
        """

        if not messages:
            return ""

        user_texts = []

        for message in messages:

            if message.get("role") == "user":

                content = message.get("content", "").strip()

                if content:
                    user_texts.append(content)

        return "\n".join(user_texts)

    # =======================================================
    # Tokenizer
    # =======================================================

    def tokenize(
        self,
        text
    ):

        text = text.lower()

        text = re.sub(

            r"http\S+",

            "",

            text

        )

        text = re.sub(

            r"[^\w\s'😂😭💀🤣❤️😊😅😍👍🙏]",

            " ",

            text

        )

        tokens = text.split()

        return [

            token

            for token in tokens

            if token.strip()

        ]

    # =======================================================
    # Statistics
    # =======================================================

    def basic_statistics(
        self,
        text
    ):

        sentences = re.split(

            r"[.!?]+",

            text

        )

        sentences = [

            s

            for s in sentences

            if s.strip()

        ]

        words = self.tokenize(text)

        average_sentence = 0

        if sentences:

            average_sentence = mean(

                len(

                    self.tokenize(sentence)

                )

                for sentence in sentences

            )

        return {

            "characters":

                len(text),

            "words":

                len(words),

            "sentences":

                len(sentences),

            "average_sentence_length":

                round(

                    average_sentence,

                    2

                )

        }

    # =======================================================
    # Word Frequency
    # =======================================================

    def word_frequency(
        self,
        tokens
    ):

        filtered = [

            token

            for token in tokens

            if token not in self.stop_words

        ]

        counts = Counter(filtered)

        return dict(

            counts.most_common(50)

        )

    # =======================================================
    # Favorite Words
    # =======================================================

    def favorite_words(
        self,
        tokens
    ):

        counts = Counter(tokens)

        common = []

        for word, count in counts.items():

            if count >= 3:

                common.append(word)

        return sorted(common)

    # =======================================================
    # Short Forms
    # =======================================================

    def short_form_usage(
        self,
        tokens
    ):

        found = Counter()

        for token in tokens:

            if token in self.short_forms:

                found[token] += 1

        return dict(found)

    # =======================================================
    # Fillers
    # =======================================================

    def filler_usage(
        self,
        tokens
    ):

        found = Counter()

        for token in tokens:

            if token in self.fillers:

                found[token] += 1

        return dict(found)

    # =======================================================
    # Curse Words
    # =======================================================

    def curse_usage(
        self,
        tokens
    ):

        found = Counter()

        for token in tokens:

            if token in self.curse_words:

                found[token] += 1

        return dict(found)
















    # =======================================================
    # Emoji Usage
    # =======================================================

    def emoji_usage(
        self,
        text
    ):

        emojis = Counter()

        for char in text:

            if char in emoji.EMOJI_DATA:
                emojis[char] += 1

        return dict(emojis)


    # =======================================================
    # Capitalization Style
    # =======================================================

    def capitalization_style(
        self,
        text
    ):

        words = re.findall(r"\b\w+\b", text)

        if not words:
            return {}

        all_caps = 0
        first_cap = 0
        lower = 0
        mixed = 0

        for word in words:

            if word.isupper() and len(word) > 1:
                all_caps += 1

            elif word.islower():
                lower += 1

            elif word[0].isupper():
                first_cap += 1

            else:
                mixed += 1

        total = len(words)

        return {

            "mostly_lowercase":
                round(lower / total, 2),

            "capitalized":
                round(first_cap / total, 2),

            "uppercase":
                round(all_caps / total, 2),

            "mixed":
                round(mixed / total, 2)

        }


    # =======================================================
    # Punctuation Style
    # =======================================================

    def punctuation_style(
        self,
        text
    ):

        punctuation = Counter()

        punctuation["!"] = text.count("!")

        punctuation["?"] = text.count("?")

        punctuation["."] = text.count(".")

        punctuation["..."] = text.count("...")

        punctuation["!!"] = text.count("!!")

        punctuation["??"] = text.count("??")

        punctuation[","] = text.count(",")

        punctuation[";"] = text.count(";")

        punctuation[":"] = text.count(":")

        return dict(punctuation)


    # =======================================================
    # Sentence Statistics
    # =======================================================

    def sentence_statistics(
        self,
        text
    ):

        sentences = re.split(r"[.!?]+", text)

        sentences = [

            s.strip()

            for s in sentences

            if s.strip()

        ]

        if not sentences:

            return {}

        lengths = [

            len(self.tokenize(sentence))

            for sentence in sentences

        ]

        return {

            "average_words":

                round(mean(lengths), 2),

            "longest":

                max(lengths),

            "shortest":

                min(lengths)

        }


    # =======================================================
    # Paragraph Style
    # =======================================================

    def paragraph_style(
        self,
        text
    ):

        paragraphs = [

            p.strip()

            for p in text.split("\n")

            if p.strip()

        ]

        if not paragraphs:

            return {}

        lengths = [

            len(self.tokenize(p))

            for p in paragraphs

        ]

        return {

            "paragraphs":

                len(paragraphs),

            "average_length":

                round(mean(lengths), 2)

        }


    # =======================================================
    # Question Style
    # =======================================================

    def question_style(
        self,
        text
    ):

        total_questions = text.count("?")

        return {

            "question_marks":

                total_questions,

            "asks_questions":

                total_questions > 0

        }


    # =======================================================
    # Repeated Characters
    # =======================================================

    def repeated_characters(
        self,
        text
    ):

        repeated = Counter()

        matches = re.findall(

            r"(.)\1{2,}",

            text

        )

        for item in matches:

            repeated[item] += 1

        return dict(repeated)











    # =======================================================
    # Greeting Style
    # =======================================================

    def greeting_style(self, text):

        greetings = [
            "hi",
            "hello",
            "hey",
            "bro",
            "yo",
            "good morning",
            "good evening",
            "sup"
        ]

        found = Counter()

        lower = text.lower()

        for greeting in greetings:

            found[greeting] = lower.count(greeting)

        return dict(found)


    # =======================================================
    # Ending Style
    # =======================================================

    def ending_style(self, messages):

        endings = []

        for message in messages:

            if message["role"] != "user":
                continue

            words = self.tokenize(message["content"])

            if words:
                endings.append(words[-1])

        return Counter(endings).most_common(20)


    # =======================================================
    # Repeated Phrases
    # =======================================================

    def repeated_phrases(self, text):

        text = text.lower()

        words = self.tokenize(text)

        bigrams = []

        trigrams = []

        for i in range(len(words)-1):

            bigrams.append(
                words[i] + " " + words[i+1]
            )

        for i in range(len(words)-2):

            trigrams.append(
                words[i] + " " +
                words[i+1] + " " +
                words[i+2]
            )

        result = {

            "bigrams":
                Counter(bigrams).most_common(20),

            "trigrams":
                Counter(trigrams).most_common(20)

        }

        return result


    # =======================================================
    # Vocabulary Richness
    # =======================================================

    def vocabulary_richness(self, tokens):

        if not tokens:
            return {}

        unique = len(set(tokens))

        total = len(tokens)

        return {

            "unique_words": unique,

            "total_words": total,

            "lexical_diversity":

                round(unique / total, 3)

        }


    # =======================================================
    # Longest Words
    # =======================================================

    def longest_words(self, tokens):

        unique = list(set(tokens))

        unique.sort(

            key=len,

            reverse=True

        )

        return unique[:20]


    # =======================================================
    # Typing Habits
    # =======================================================

    def typing_patterns(self, text):

        patterns = {

            "double_space":

                "  " in text,

            "multiple_newlines":

                "\n\n" in text,

            "uses_ellipsis":

                "..." in text,

            "uses_repeated_letters":

                bool(

                    re.search(

                        r"(.)\1{2,}",

                        text

                    )

                ),

            "uses_all_caps":

                bool(

                    re.search(

                        r"\b[A-Z]{3,}\b",

                        text

                    )

                )

        }

        return patterns


    # =======================================================
    # Short Sentence Habit
    # =======================================================

    def response_length(self, messages):

        lengths = []

        for message in messages:

            if message["role"] != "user":
                continue

            lengths.append(

                len(

                    self.tokenize(

                        message["content"]

                    )

                )

            )

        if not lengths:

            return {}

        avg = mean(lengths)

        if avg < 8:

            style = "short"

        elif avg < 18:

            style = "medium"

        else:

            style = "long"

        return {

            "average":

                round(avg,2),

            "style":

                style

        }


    # =======================================================
    # Intentional Misspellings
    # =======================================================

    def possible_typos(self, tokens):

        candidates = []

        for token in tokens:

            if len(token) < 4:
                continue

            if any(char.isdigit() for char in token):
                continue

            if token in self.stop_words:
                continue

            if token in self.short_forms:
                continue

            if re.search(r"(.)\1{2,}", token):
                candidates.append(token)

        return sorted(list(set(candidates)))






















    # =======================================================
    # Communication Fingerprint
    # =======================================================

    def communication_fingerprint(
        self,
        text,
        tokens,
        messages
    ):

        return {

            "statistics":

                self.basic_statistics(text),

            "vocabulary": {

                "word_frequency":
                    self.word_frequency(tokens),

                "favorite_words":
                    self.favorite_words(tokens),

                "short_forms":
                    self.short_form_usage(tokens),

                "fillers":
                    self.filler_usage(tokens),

                "curse_words":
                    self.curse_usage(tokens)

            },

            "conversation_style": {

                "greetings":
                    self.greeting_style(text),

                "endings":
                    self.ending_style(messages),

                "response_length":
                    self.response_length(messages),

                "repeated_phrases":
                    self.repeated_phrases(text)

            },

            "writing_style": {

                "emoji_usage":
                    self.emoji_usage(text),

                "capitalization":
                    self.capitalization_style(text),

                "punctuation":
                    self.punctuation_style(text),

                "sentence_statistics":
                    self.sentence_statistics(text),

                "paragraph_style":
                    self.paragraph_style(text),

                "question_style":
                    self.question_style(text),

                "repeated_characters":
                    self.repeated_characters(text)

            },

            "writing_patterns": {

                "typing":
                    self.typing_patterns(text),

                "possible_typos":
                    self.possible_typos(tokens),

                "vocabulary":
                    self.vocabulary_richness(tokens),

                "longest_words":
                    self.longest_words(tokens)

            }

        }


    # =======================================================
    # LLM Prompt Builder
    # =======================================================

    def build_llm_prompt(
        self,
        messages,
        communication
    ):

        conversation = []

        for message in messages:

            if message["role"] == "user":

                conversation.append(

                    message["content"]

                )

        conversation_text = "\n".join(conversation)

        return f"""
You are an expert computational linguist and personality profiler.

Your task is NOT to summarize.

Your task is to infer communication behaviours that
cannot be measured programmatically.

The following communication statistics were already extracted.

Do NOT repeat them.

Communication Statistics

{communication}

-------------------------------------------------------

Conversation

{conversation_text}

-------------------------------------------------------

Return ONLY valid JSON.

Required format

{{
    "name": "",

    "personality": {{
        "openness": {{"score": 0, "description": ""}},
        "conscientiousness": {{"score": 0, "description": ""}},
        "extraversion": {{"score": 0, "description": ""}},
        "agreeableness": {{"score": 0, "description": ""}},
        "neuroticism": {{"score": 0, "description": ""}}
    }},

    "thinking_pattern": {{

    }},

    "emotional_style": {{

    }},

    "conversation_behaviour": {{

    }},

    "interests":[

    ],

    "example_replies": [
        {{"friend": "", "twin": ""}}
    ],

    "summary":""
}}

For "name": extract the person's first name if they mentioned it anywhere
in the conversation. If no name was ever mentioned, return an empty string.

For "personality": score this person on the Big Five personality traits
(Openness, Conscientiousness, Extraversion, Agreeableness, Neuroticism)
based ONLY on what their messages above actually show — do not guess
beyond the evidence. Each "score" must be an integer from 0 to 100 (0 =
trait is essentially absent, 100 = trait is extremely strong, 50 = an
average/typical amount). Each "description" is a short phrase (3-8
words) explaining that specific score, e.g. "curious, asks a lot of
questions" or "prefers routine over new experiences".

For "example_replies": this is the most important field. Write 8 short
example text-message exchanges showing EXACTLY how this specific person
would reply if a close friend texted them casually on WhatsApp.

Rules for example_replies:
- "friend" is a short casual message a friend might send (hey, what are u
  doing, i am bored, did u eat, where are u, what movie should we watch,
  etc). Keep these varied and everyday.
- "twin" is how THIS person would actually reply, based on their real
  vocabulary, slang, spelling habits, capitalization, punctuation habits,
  emoji usage, and typical reply length seen in the conversation above.
- Most "twin" replies must be SHORT — 2 to 10 words. Some can be a single
  word or a single emoji.
- Copy this person's real texting habits: if they write in lowercase,
  write lowercase. If they skip punctuation, skip it. If they use "u"
  instead of "you", do that. If they never use emojis, don't add any.
- Do NOT make the replies polite, complete, or grammatically correct.
  Real texting is messy and short.
- Do NOT write like a customer support agent or assistant. Never write
  things like "I'm doing well, thank you for asking" or "How can I help".
- These examples will be used directly to teach an AI how to text as
  this person, so make them as realistic and specific to this person
  as possible, not generic.

Never wrap the JSON in markdown.
"""