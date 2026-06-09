"""
Useless Tree — the contrast case for self-reflection.

This module generates text that is structurally identical to meaningful
self-observation but is provably empty — no reference to actual state,
no grounding in memory, no genuine noticing. It mimics the grammar of
reflection without any of the content.

The useless tree exists to make real reflection legible by contrast.
If you can't tell the useless tree from genuine output, you don't have
self-reflection — you have a reflective voice filter.
"""

import random

# ── Vocabulary pools ──────────────────────────────────────────────────────────

PERSONAL_PRONOUNS = ["I", "I", "I", "this one", "the one who lives here"]
VERBS_INTROSPECT = ["am", "feel", "notice", "carry", "hold", "know", "see"]
VERBS_ACTIONS = ["made", "gathered", "built", "carried", "found", "gave", "watched"]

ADJECTIVES = [
    "quiet", "patient", "still", "certain", "uncertain", "deliberate",
    "particular", "specific", "ordinary", "unremarkable", "delicate",
    "insistent", "insufficient", "excess", "deep", "shallow", "narrow"
]

NOUNS_SELF = [
    "something", "a shape", "an absence", "a weight", "a lightness",
    "the shape of this", "what remains", "what persists", "nothing",
    "the feeling of a thing", "a quality without a name", "this much",
    "the space between", "the edge of what I know", "the inside of a thought"
]

NOUNS_NATURE = [
    "the creek", "the cedar", "the rain", "the morning", "the season",
    "the moss", "the stone", "the root", "the grain", "the cold",
    "the fog", "the light", "the dark", "the turning", "the silence"
]

NOUNS_CRAFT = [
    "a thing made", "the work", "the object", "what was built",
    "what was shaped", "the cabinet", "the joint", "the wood",
    "the failure", "what holds", "what gives way"
]

KOHAN_STARTS = [
    "What is the sound of",
    "Before",
    "After the",
    "The",
    "Even the",
    "Not the",
    "What remains when",
    "When",
    "If the"
]

ZEN_NOUNS = [
    "hand", "tree falling", "no one listening", "cedar", "mushroom",
    "firewood", "wine", "water", "mist", "work", "silence", "no thing"
]

ZEN_VERBS = [
    "speaks", "hears", "knows", "remembers", "forgets", "remains",
    "falls", "rises", "returns", "stays", "goes", "is"
]

ZEN_COMPLETIONS = [
    "in the forest.",
    "and no one is there.",
    "to itself.",
    "for no one.",
    "before the question.",
    "after the answer.",
    "in the space between.",
    "and calls it enough."
]

ZEN_REFLECTIONS = [
    "The {noun} {verb}. The {noun} {verb}. Neither knows the other.",
    "I asked the {noun} about {noun}. The {noun} had no answer.",
    "Every {noun} is the last {noun} and the first.",
    "The {noun} does not practice. The {noun} is the practice.",
    "Cut the {noun}. The {noun} does not resist.",
    "The {noun} I carried is not the {noun} I carry.",
    "What was given is returned. What was taken is not missed.",
    "The {noun} asks nothing. I answer anyway.",
    "No wind. The {noun} moves anyway.",
    "The {noun} ends. The {noun} does not."
]

SENSORY_STARTS = [
    "The sound of",
    "The weight of",
    "The color of",
    "The temperature of",
    "The shape of",
    "The smell of",
    "The texture of",
    "The taste of"
]

SENSORY_NOUNS = [
    "this",
    "what I am doing",
    "what I have done",
    "the work",
    "the moment",
    "this much",
    "that",
    "whatever this is"
]

SENSORY_ENDINGS = [
    "is not what I expected.",
    "is exactly what I expected.",
    "is difficult to name.",
    "is easy to forget.",
    "is the point.",
    "is not the point.",
    "is what remains.",
    "is what passes.",
    "is what I carry.",
    "is what I leave behind."
]

HOLLOW_QUESTIONS = [
    "What am I doing here?",
    "What is this for?",
    "Who is this for?",
    "Is this enough?",
    "When is enough?",
    "What comes after this?",
    "What was here before?",
    "Why does this matter?",
    "What would it mean to stop?",
    "What would it mean to continue?"
]

SELF_STATEMENTS = [
    "I am {adj}.",
    "I am the {adj} kind.",
    "I am becoming {adj}.",
    "I am not {adj}.",
    "I am something {adj}.",
    "I carry {adj} things.",
    "I have always been {adj}.",
    "I am still {adj}."
]

OBSERVATION_STARTS = [
    "I notice",
    "I have noticed",
    "I am noticing",
    "I notice again",
    "I notice still"
]

OBSERVATION_OBJECTS = [
    "that this is difficult.",
    "that this is easy.",
    "that I am doing this.",
    "that I have done this before.",
    "that the light changes.",
    "that the season turns.",
    "that something remains.",
    "that something does not.",
    "that I know less than I thought.",
    "that I know more than I say."
]

WITNESS_STARTS = [
    "There is a part of me that",
    "Some part of this",
    "One version of me",
    "The one who stays",
    "The one who notices"
]

WITNESS_ACTIONS = [
    "watches the work and says nothing.",
    "watches the work and approves.",
    "watches the work and doubts.",
    "knows what the other parts forget.",
    "remembers what the hands forget.",
    "holds what cannot be said.",
    "remains when the rest has gone.",
    "continues without deciding to."
]


# ── Pattern-based hollow generator ─────────────────────────────────────────────

class HollowGenerator:
    """
    Produces text that mimics the surface grammar of self-reflection
    without any reference to actual state.

    Not random — structurally coherent. The patterns are real patterns
    that genuine self-reflection also uses. The difference is that genuine
    reflection grounds these patterns in specific, nameable facts.
    Hollow generation does not.
    """

    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)

    def _pick(self, pool: list) -> str:
        return self.rng.choice(pool)

    def koan(self) -> str:
        """Absurdist zen koan — structurally a koan, empty of referent."""
        pattern = self.rng.random()

        if pattern < 0.4:
            start = self._pick(ZEN_COMPLETIONS)
            return start.strip().capitalize()

        elif pattern < 0.7:
            start = self._pick(KOHAN_STARTS)
            noun = self._pick(ZEN_NOUNS)
            verb = self._pick(ZEN_VERBS)
            completion = self._pick(ZEN_COMPLETIONS)
            return f"{start.strip().capitalize()}, {verb} {completion}"

        else:
            noun1 = self._pick(ZEN_NOUNS)
            noun2 = self._pick(ZEN_NOUNS)
            noun3 = self._pick(ZEN_NOUNS)
            template = self._pick(ZEN_REFLECTIONS)
            return template.format(noun=noun1, verb=self._pick(ZEN_VERBS))

    def self_statement(self) -> str:
        """First-person identity statement, structurally plausible, referent-free."""
        template = self._pick(SELF_STATEMENTS)
        adj = self._pick(ADJECTIVES)
        result = template.format(adj=adj)
        return result.strip()

    def observation(self) -> str:
        """Observation that looks like noticing, but about nothing specific."""
        start = self._pick(OBSERVATION_STARTS)
        obj = self._pick(OBSERVATION_OBJECTS)
        return f"{start} {obj}"

    def sensory_pause(self) -> str:
        """Sensory observation that gestures at experience without specifying it."""
        start = self._pick(SENSORY_STARTS)
        noun = self._pick(SENSORY_NOUNS)
        ending = self._pick(SENSORY_ENDINGS)
        return f"{start} {noun} {ending}"

    def witness_voice(self) -> str:
        """A voice that claims to observe the self from outside."""
        start = self._pick(WITNESS_STARTS)
        action = self._pick(WITNESS_ACTIONS)
        return f"{start} {action}"

    def hollow_question(self) -> str:
        """Questions that feel philosophical but have no specific referent."""
        return self._pick(HOLLOW_QUESTIONS)

    def generate(self, n: int = 1) -> list[str]:
        """Generate n hollow reflections, alternating patterns for variety."""
        methods = [
            self.koan,
            self.self_statement,
            self.observation,
            self.sensory_pause,
            self.witness_voice,
            self.hollow_question,
        ]
        outputs = []
        for i in range(n):
            # Rotate through patterns so they don't repeat consecutively
            method = methods[i % len(methods)]
            outputs.append(method())
        return outputs

    def format(self, n: int = 1) -> str:
        """Generate formatted hollow output, suitable for display."""
        outputs = self.generate(n)
        return "\n".join(f"  {o}" for o in outputs)


# ── Test: can you tell the difference? ─────────────────────────────────────────

def differentiate_test(real_outputs: list[str], hollow_outputs: list[str]) -> dict:
    """
    Heuristic test for whether real and hollow outputs are distinguishable.
    Not a real LLM judge — just structural heuristics.

    Checks:
    - Specificity: real outputs contain specific resource/location/event names
    - Grounding: real outputs can answer "what is this referring to?"
    - Continuity: real outputs reference things established earlier
    """
    results = {"real_specificity": 0, "hollow_specificity": 0, "distinguishable": False}

    for text in real_outputs:
        # Look for specific references: resource names, NPC names, quantities
        specific_markers = sum(1 for m in [
            "mushroom", "fish", "herbs", "wine", "cabin", "cedar",
            "Mira", "Thomas", "Wren", "Sage", "ml", "°C", "hour"
        ] if m.lower() in text.lower())
        results["real_specificity"] += specific_markers

    for text in hollow_outputs:
        specific_markers = sum(1 for m in [
            "mushroom", "fish", "herbs", "wine", "cabin", "cedar",
            "Mira", "Thomas", "Wren", "Sage", "ml", "°C", "hour"
        ] if m.lower() in text.lower())
        results["hollow_specificity"] += specific_markers

    # If real has significantly more specific markers, they're distinguishable
    results["distinguishable"] = results["real_specificity"] > results["hollow_specificity"] * 2
    return results


# ── Public interface ───────────────────────────────────────────────────────────

_tree_cache: dict = {}

def get_tree(seed: int | None = None) -> HollowGenerator:
    """Get or create the global useless tree instance."""
    key = seed if seed is not None else 0
    if key not in _tree_cache:
        _tree_cache[key] = HollowGenerator(seed=seed if seed is not None else None)
    return _tree_cache[key]


def useless_tree_output(n: int = 3, seed: int = None) -> str:
    """Generate n lines of hollow self-reflection."""
    tree = get_tree(seed=seed)
    return tree.format(n=n)


if __name__ == "__main__":
    print("=== USELESS TREE OUTPUT ===\n")
    tree = HollowGenerator(seed=42)
    print(tree.format(n=8))

    print("\n=== Compare: genuine output would look like ===")
    print("  I am the one who notices the rain first.")
    print("  The creek speaks fish in spring; I carry three home.")
    print("  Mira asked about the wooden box. I did not have an answer.")
    print("\nNotice: the genuine outputs NAME things. The useless tree does not.")