package com.example.dronebuddyapp.voice

// Turns what the user said into one of the 6 commands.
//   "where is my mug"   -> WHERE_IS cup
//   "Louder!"           -> LOUDER
//   "where are my keys" -> not sent (YOLO can't see keys)
//   "nice weather"      -> ignored
// Rules: only commands go to Python (never raw text); short commands like
// "stop" must be the whole sentence, so "where is the stop sign" is a search.
// Pure Kotlin (no Android), so it runs in plain unit tests.
object VoiceCommandParser {

    // Below this the result is dropped. Placeholder: tune it from real recordings.
    const val DEFAULT_MIN_CONFIDENCE = 0.5f

    // What parse() can return
    sealed class Result {
        // A valid command: send it to Python
        data class Recognized(val command: VoiceCommand) : Result()

        // Asked for something YOLO can't detect (keys, wallet, door): not sent
        data class UnsupportedObject(val spokenObject: String, val heardText: String) : Result()

        // Recognizer wasn't sure enough: dropped
        data class LowConfidence(val heardText: String, val confidence: Float) : Result()

        // Not one of the 6 commands: ignored
        object NotACommand : Result()
    }

    // ---- Vocabulary (compared after normalize(): lowercase, no punctuation) ----

    private val START_PHRASES = setOf(
        "start", "start session", "begin", "hey buddy", "hi buddy", "hello buddy",
        "visual buddy", "hey visual buddy", "wake up",
    )
    private val STOP_PHRASES = setOf(
        "stop", "end", "end session", "stop session", "quit", "goodbye", "bye",
        "bye buddy", "that is all",
    )
    private val REPEAT_PHRASES = setOf(
        "repeat", "say again", "say that again", "again", "what", "what did you say",
        "pardon", "come again", "repeat that", "one more time",
    )
    private val LOUDER_PHRASES = setOf(
        "louder", "volume up", "speak up", "turn it up", "turn up", "more volume", "too quiet",
    )
    private val QUIETER_PHRASES = setOf(
        "quieter", "softer", "volume down", "turn it down", "turn down", "less volume",
        "too loud", "lower",
    )

    // How a WHERE_IS starts; the object name comes after. Longest first.
    private val WHERE_IS_PREFIXES = listOf(
        "can you find", "help me find", "where did i put", "is there a", "is there an",
        "where is", "where are", "look for", "search for", "find", "locate",
    )

    // Ignored words: "stop please" -> "stop"
    private val FILLER_WORDS = setOf(
        "please", "um", "uh", "hmm", "okay", "ok", "so", "now", "buddy", "thanks", "thank", "you",
    )

    // Removed from object names: "my cup" -> "cup"
    private val ARTICLE_WORDS = setOf("my", "the", "a", "an", "some", "any", "our", "your", "this", "that")

    // All 80 objects our model yolo11n.pt can detect (COCO classes), spelled exactly
    // as YOLO prints them: Python searches by this exact name. Complete for yolo11n.pt;
    // replace it if the team changes model. Print the real list with:
    //   python -c "from ultralytics import YOLO; print(list(YOLO('yolo11n.pt').names.values()))"
    val YOLO_CLASSES: Set<String> = setOf(
        "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck",
        "boat", "traffic light", "fire hydrant", "stop sign", "parking meter", "bench",
        "bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra",
        "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee",
        "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove",
        "skateboard", "surfboard", "tennis racket", "bottle", "wine glass", "cup",
        "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
        "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch",
        "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse",
        "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
        "refrigerator", "book", "clock", "vase", "scissors", "teddy bear",
        "hair drier", "toothbrush",
    )

    // Everyday words -> YOLO name
    private val SYNONYMS: Map<String, String> = mapOf(
        "mug" to "cup", "coffee cup" to "cup", "glass of water" to "cup",
        "bag" to "backpack", "school bag" to "backpack", "rucksack" to "backpack",
        "purse" to "handbag",
        "phone" to "cell phone", "cellphone" to "cell phone", "mobile" to "cell phone",
        "mobile phone" to "cell phone", "smartphone" to "cell phone", "iphone" to "cell phone",
        "table" to "dining table", "desk" to "dining table",
        "sofa" to "couch",
        "television" to "tv", "tv set" to "tv", "t v" to "tv",
        "computer" to "laptop", "macbook" to "laptop",
        "fridge" to "refrigerator",
        "plant" to "potted plant", "flower pot" to "potted plant",
        "bike" to "bicycle", "motorbike" to "motorcycle",
        "water bottle" to "bottle",
        "ball" to "sports ball",
        "remote control" to "remote",
        "hair dryer" to "hair drier",
        "doughnut" to "donut",
        "people" to "person", "someone" to "person", "somebody" to "person",
        "anyone" to "person", "anybody" to "person", "man" to "person", "woman" to "person",
        "puppy" to "dog", "kitten" to "cat",
        "seat" to "chair", "stool" to "chair",
        "toilet seat" to "toilet",
        "glass" to "wine glass",
    )

    // ---- Public API ----

    // One heard sentence -> Result. confidence < 0 means "no score" (treated as sure).
    fun parse(
        heardText: String,
        confidence: Float = 1.0f,
        minConfidence: Float = DEFAULT_MIN_CONFIDENCE,
    ): Result {
        val score = if (confidence < 0f) 1.0f else confidence
        val text = normalize(heardText)
        if (text.isEmpty()) return Result.NotACommand

        // 1. WHERE_IS first, so "where is the stop sign" is a search, not STOP.
        val whereIs = matchWhereIs(text, heardText, score)

        // 2. Otherwise one of the short commands, as the whole utterance.
        val short = whereIs ?: matchShortCommand(text)?.let {
            Result.Recognized(VoiceCommand(it, null, heardText, score))
        } ?: return Result.NotACommand

        // 3. Drop low-confidence results only once we know it was a command,
        //    so the log can tell "unsure" apart from "not a command".
        if (score < minConfidence) return Result.LowConfidence(heardText, score)
        return short
    }

    // Android gives several guesses, best first: use the first one that is a command
    fun parseBest(
        alternatives: List<String>,
        confidences: FloatArray? = null,
        minConfidence: Float = DEFAULT_MIN_CONFIDENCE,
    ): Result {
        var fallback: Result = Result.NotACommand
        alternatives.forEachIndexed { i, text ->
            val conf = confidences?.getOrNull(i) ?: -1f
            when (val r = parse(text, conf, minConfidence)) {
                is Result.Recognized -> return r
                Result.NotACommand -> Unit
                else -> if (fallback == Result.NotACommand) fallback = r
            }
        }
        return fallback
    }

    // Spoken object -> YOLO name, or null: "my mug" -> cup, "chairs" -> chair, "keys" -> null
    fun toYoloClass(spoken: String): String? {
        val words = normalize(spoken).split(" ").filter { it.isNotEmpty() && it !in ARTICLE_WORDS }
        if (words.isEmpty()) return null
        val phrase = words.joinToString(" ")

        // Whole phrase first, then the last 2 words, then the last word
        // ("my red coffee mug" -> "coffee mug" -> cup).
        val tails = listOf(phrase) + (minOf(2, words.size) downTo 1).map { words.takeLast(it).joinToString(" ") }
        for (tail in tails) {
            lookup(tail)?.let { return it }
            for (s in singulars(tail)) lookup(s)?.let { return it }
        }
        return null
    }

    // ---- Internals ----

    private fun matchWhereIs(text: String, heardText: String, score: Float): Result? {
        val prefix = WHERE_IS_PREFIXES.firstOrNull { text == it || text.startsWith("$it ") } ?: return null
        var rest = text.removePrefix(prefix).trim()
        // "where is my cup please", "find the chair for me"
        rest = rest.removeSuffix(" for me").trim()
        if (rest.isEmpty() || rest.split(" ").all { it in ARTICLE_WORDS }) return null // just "find"

        val label = toYoloClass(rest)
        return if (label != null) {
            Result.Recognized(VoiceCommand(CommandType.WHERE_IS, label, heardText, score))
        } else {
            Result.UnsupportedObject(rest.split(" ").filter { it !in ARTICLE_WORDS }.joinToString(" "), heardText)
        }
    }

    private fun matchShortCommand(text: String): CommandType? {
        val stripped = text.split(" ").filter { it !in FILLER_WORDS }.joinToString(" ")
        // Check both: "hey buddy" contains the filler word "buddy".
        for (candidate in listOf(text, stripped)) {
            when (candidate) {
                in START_PHRASES -> return CommandType.START_SESSION
                in STOP_PHRASES -> return CommandType.STOP_SESSION
                in REPEAT_PHRASES -> return CommandType.REPEAT
                in LOUDER_PHRASES -> return CommandType.LOUDER
                in QUIETER_PHRASES -> return CommandType.QUIETER
            }
        }
        return null
    }

    private fun lookup(phrase: String): String? = when (phrase) {
        in YOLO_CLASSES -> phrase
        in SYNONYMS -> SYNONYMS[phrase]
        else -> null
    }

    // Possible singulars of a plural: cups -> cup, buses -> bus, knives -> knife
    private fun singulars(word: String): List<String> {
        if (!word.endsWith("s") || word.endsWith("ss")) return emptyList()
        val out = mutableListOf<String>()
        if (word.endsWith("ives")) out += word.dropLast(3) + "fe"  // knives -> knife
        if (word.endsWith("ies")) out += word.dropLast(3) + "y"
        if (word.endsWith("es")) out += word.dropLast(2)           // buses, benches, glasses
        out += word.dropLast(1)                                     // cups, vases
        return out
    }

    // Lowercase, "where's" -> "where is", remove punctuation and extra spaces
    internal fun normalize(raw: String): String {
        var t = raw.lowercase()
        t = t.replace("’", "'")
            .replace("where's", "where is")
            .replace("what's", "what is")
            .replace("that's", "that is")
            .replace("[unk]", " ")
        t = t.replace(Regex("[^a-z0-9' ]"), " ")
        t = t.replace("'", "")
        return t.split(Regex("\\s+")).filter { it.isNotEmpty() }.joinToString(" ")
    }
}
