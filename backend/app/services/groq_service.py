"""
Groq Service for Chain Answer Game
Handles word generation and validation using Groq Cloud API
"""
import logging
import os
from typing import List, Optional
from groq import Groq

logger = logging.getLogger(__name__)

# Get from environment at runtime
# List of models in fallback order. Override the default with GROQ_MODEL when
# a deployment needs a different model available to its Groq account.
AVAILABLE_MODELS = [
    "openai/gpt-oss-120b",
    "qwen/qwen3.6-27b",
    "meta-llama/llama-4-scout-17b-16e-instruct",
]

DEFAULT_MODEL = os.getenv("GROQ_MODEL", AVAILABLE_MODELS[0])
VISION_MODELS = [
    "llama-3.2-11b-vision-preview",
    "llama-3.2-90b-vision-preview",
    "llama-3.2-11b-vision",
    "llama-3.2-90b-vision",
    "llava-v1.5-7b-4096-preview" 
]

logger.info(f"Groq service configured with default model: {DEFAULT_MODEL}")





class GroqService:
    """Service to interact with Groq Cloud API for word generation and validation"""

    _initialized = False
    _available = False
    _client = None

    @classmethod
    def initialize(cls):
        """Initialize Groq service - called on startup"""
        if cls._initialized:
            return

        cls._initialized = True
        logger.info("="*60)
        logger.info("Groq Service Initialization")
        logger.info("="*60)
        logger.info(f"Model: {DEFAULT_MODEL}")

        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            logger.error(" GROQ_API_KEY not set in environment")
            cls._available = False
        else:
            try:
                cls._client = Groq(api_key=groq_api_key)
                cls._available = cls.is_groq_available()
                if cls._available:
                    logger.info(f" Groq Connected and Ready")
                else:
                    logger.warning(
                        "️  Groq service check failed - using fallback validator")
            except Exception as e:
                logger.error(f" Failed to initialize Groq: {e}")
                cls._available = False
        logger.info("="*60)



    @staticmethod
    def is_groq_available() -> bool:
        """Check if Groq service is available"""
        if not GroqService._client:
            logger.warning("Groq client not initialized")
            return False

        try:
            # Test the API with a simple request
            GroqService._client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": "Say 'OK'"
                    }
                ],
                model=DEFAULT_MODEL,
                max_tokens=10,
            )
            logger.info(" Groq service is available and responding")
            return True
        except Exception as e:
            logger.warning(f"Groq availability check failed: {e}")
            return False

    @staticmethod
    def _build_fallback_lesson_plan(topic: str, syllabus_context: Optional[str] = None) -> dict:
        """Build a topic-aware lesson plan when the AI response is empty or malformed."""
        context_line = (
            f"Use the syllabus context as a guide: {syllabus_context}."
            if syllabus_context
            else "Adapt the lesson to the learner's level and classroom pace."
        )

        return {
            "success": True,
            "error": None,
            "lecture_flow": (
                f"1. Introduce {topic} and state the learning goals.\n"
                f"2. Explain the core idea of {topic} with a simple definition.\n"
                f"3. Demonstrate one worked example step by step.\n"
                f"4. Give students guided practice with feedback.\n"
                f"5. End with a recap and a quick check for understanding.\n"
                f"Note: {context_line}"
            ),
            "examples": (
                f"1. A basic example showing how {topic} works in practice.\n"
                f"2. A second example with a small variation or edge case.\n"
                f"3. A common mistake example to help students avoid errors.\n"
                f"4. A real-world example that connects {topic} to classwork or exams."
            ),
            "activities": (
                f"1. Think-pair-share: explain {topic} in pairs.\n"
                f"2. Guided problem solving: complete one example together.\n"
                f"3. Small-group challenge: solve a similar question independently.\n"
                f"4. Exit ticket: write one takeaway and one question."
            ),
            "quiz_questions": (
                f"1. What is {topic}?\n"
                f"2. What is the first step when approaching {topic} problems?\n"
                f"3. Which example best illustrates {topic}?\n"
                f"4. What common mistake should students avoid?\n"
                f"5. How would you explain {topic} in one sentence?"
            ),
        }

    @staticmethod
    def generate_lesson_plan(topic: str, syllabus_context: Optional[str] = None) -> dict:
        """
        Generate a comprehensive lesson plan using Groq AI.

        Args:
            topic: The lesson topic (e.g., "Recursion in C++", "Photosynthesis")
            syllabus_context: Optional syllabus details or context

        Returns:
            {
                "lecture_flow": str,
                "examples": str,
                "activities": str,
                "quiz_questions": str,
                "success": bool,
                "error": Optional[str]
            }
        """
        if not GroqService._client:
            logger.warning("Groq client not initialized for lesson generation")
            return {
                "success": False,
                "error": "Groq service not available",
                "lecture_flow": "",
                "examples": "",
                "activities": "",
                "quiz_questions": ""
            }

        try:
            context_text = f"\nContext: {syllabus_context}" if syllabus_context else ""

            prompt = f"""Create a detailed and comprehensive lesson plan for the topic: "{topic}"{context_text}

You MUST format your response EXACTLY as follows. Do not deviate from this structure:

LECTURE FLOW:
[Provide detailed lecture flow with introduction, core concepts, practical application, and summary]

EXAMPLES:
[Provide 3-5 concrete, practical examples relevant to the topic with explanations]

ACTIVITIES:
[Provide 3-4 interactive classroom activities that engage students and reinforce learning]

QUIZ QUESTIONS:
[Provide 5-10 multiple choice questions to test understanding of the topic]

Important: Each section must have real, detailed content below its header. Do not leave sections empty."""

            try:
                message = GroqService._client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model=DEFAULT_MODEL,
                    temperature=0.7,
                    max_tokens=2000,
                )
                response_text = message.choices[0].message.content
            except Exception as e:
                if "decommissioned" in str(e).lower() or "model" in str(e).lower():
                    logger.warning(
                        f"Model {DEFAULT_MODEL} not available, trying alternatives")
                    for alt_model in AVAILABLE_MODELS[1:]:
                        try:
                            message = GroqService._client.chat.completions.create(
                                messages=[{"role": "user", "content": prompt}],
                                model=alt_model,
                                temperature=0.7,
                                max_tokens=2000,
                            )
                            response_text = message.choices[0].message.content
                            logger.info(
                                f"Successfully used alternative model: {alt_model}")
                            break
                        except Exception:
                            continue
                    else:
                        logger.error("All models failed for lesson generation")
                        return {
                            "success": False,
                            "error": "All AI models failed",
                            "lecture_flow": "",
                            "examples": "",
                            "activities": "",
                            "quiz_questions": ""
                        }
                else:
                    raise

            # Parse the structured response with improved error handling
            sections = {
                "lecture_flow": "",
                "examples": "",
                "activities": "",
                "quiz_questions": ""
            }

            current_section = None
            section_markers = {
                "LECTURE FLOW": "lecture_flow",
                "EXAMPLES": "examples",
                "ACTIVITIES": "activities",
                "QUIZ QUESTIONS": "quiz_questions"
            }

            logger.info(f"Raw response from Groq (length: {len(response_text)}):\n{response_text[:500]}...")

            lines = response_text.split('\n')
            for i, line in enumerate(lines):
                stripped_line = line.strip()
                
                # Skip empty lines
                if not stripped_line:
                    continue

                # Check if this line is a section marker
                section_found = False
                for marker, section_key in section_markers.items():
                    # Check if line contains the marker (case-insensitive)
                    if marker in stripped_line.upper():
                        current_section = section_key
                        section_found = True
                        logger.info(f"Found section at line {i}: {section_key} from '{stripped_line}'")
                        break

                # Add content to current section (skip section markers themselves)
                if current_section and not section_found:
                    sections[current_section] += line + "\n"

            # Clean up whitespace and ensure we have content
            for key in sections:
                sections[key] = sections[key].strip()
                if not sections[key]:
                    logger.warning(f"Section '{key}' is empty after parsing")

            if not any(sections.values()):
                logger.warning(
                    "Groq lesson parsing produced no usable content; using fallback lesson plan"
                )
                return GroqService._build_fallback_lesson_plan(topic, syllabus_context)

            fallback_sections = GroqService._build_fallback_lesson_plan(
                topic,
                syllabus_context
            )
            for key in sections:
                if not sections[key]:
                    sections[key] = fallback_sections[key]

            # Log parsing results
            logger.info(f"Parsed sections - lecture_flow: {len(sections['lecture_flow'])} chars, examples: {len(sections['examples'])} chars, activities: {len(sections['activities'])} chars, quiz_questions: {len(sections['quiz_questions'])} chars")
            logger.info(f"Generated lesson plan for topic: {topic}")
            
            return {
                "success": True,
                "error": None,
                **sections
            }

        except Exception as e:
            logger.error(f"Error generating lesson plan with Groq: {e}")
            return {
                "success": False,
                "error": str(e),
                "lecture_flow": "",
                "examples": "",
                "activities": "",
                "quiz_questions": ""
            }

    @staticmethod
    def generate_word_suggestions(
        subject: str,
        difficulty: str,
        count: int = 5,
        chain_variation: str = "standard",
        starting_word: str = "apple"
    ) -> List[str]:
        """
        Generate word suggestions using Groq AI for a given subject and difficulty.

        Args:
            subject: Topic/subject for word generation (e.g., "Science", "Animals")
            difficulty: easy, medium, hard
            count: Number of suggestions to generate (default: 5)
            chain_variation: Type of chain game (standard, category, ladder, etc.)
            starting_word: Starting word for context

        Returns:
            List of suggested words, or empty list if generation fails
        """
        if not GroqService._client:
            logger.warning("Groq client not initialized for word suggestions")
            return []

        try:
            difficulty_hint = {
                "easy": "common, simple words",
                "medium": "moderate difficulty words",
                "hard": "challenging, uncommon words"
            }.get(difficulty, "common words")

            prompt = f"""Generate exactly {count} English words related to "{subject}" that are {difficulty_hint}.
These words will be used in a word chain game starting with "{starting_word}".
For a {chain_variation} chain game.
Return ONLY the words, one per line, no numbering, no explanations."""

            try:
                message = GroqService._client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model=DEFAULT_MODEL,
                    temperature=0.7,
                    max_tokens=200,
                )
                generated_text = message.choices[0].message.content
            except Exception as e:
                if "decommissioned" in str(e).lower() or "model" in str(e).lower():
                    for alt_model in AVAILABLE_MODELS[1:]:
                        try:
                            message = GroqService._client.chat.completions.create(
                                messages=[{"role": "user", "content": prompt}],
                                model=alt_model,
                                temperature=0.7,
                                max_tokens=200,
                            )
                            generated_text = message.choices[0].message.content
                            break
                        except Exception:
                            continue
                    else:
                        logger.error("All models failed for word generation")
                        return []
                else:
                    raise

            # Parse words from response
            words = [w.strip().lower() for w in generated_text.split('\n') if w.strip()]
            valid_words = [w for w in words if w.isalpha() and 2 <= len(w) <= 15]

            logger.info(f"Generated {len(valid_words)} suggestions for subject: {subject}")
            return valid_words[:count]

        except Exception as e:
            logger.error(f"Error generating words with Groq: {e}")
            return []

    @staticmethod
    def validate_word_semantic(
        word: str,
        subject: str,
        previous_word: str,
        chain_context: List[str]
    ) -> tuple:
        """
        Validate if a word is semantically related to the subject using Groq AI.

        Args:
            word: Word to validate
            subject: Subject/topic context
            previous_word: Previous word in the chain
            chain_context: List of words already in the chain

        Returns:
            Tuple of (is_valid: bool, reason: str)
        """
        if not GroqService._client:
            logger.warning("Groq client not initialized for word validation")
            return False, "Validation service unavailable"

        try:
            chain_summary = ", ".join(chain_context[-3:]) if chain_context else previous_word

            prompt = f"""Is the word "{word}" semantically related to "{subject}"?
Context: This is part of a word chain about {subject}, following: {previous_word}
Chain so far: {chain_summary}

Answer with ONLY "yes" or "no", followed by a brief reason (max 10 words)."""

            try:
                message = GroqService._client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model=DEFAULT_MODEL,
                    temperature=0.3,
                    max_tokens=50,
                )
                generated_text = message.choices[0].message.content.lower().strip()
            except Exception as e:
                if "decommissioned" in str(e).lower() or "model" in str(e).lower():
                    for alt_model in AVAILABLE_MODELS[1:]:
                        try:
                            message = GroqService._client.chat.completions.create(
                                messages=[{"role": "user", "content": prompt}],
                                model=alt_model,
                                temperature=0.3,
                                max_tokens=50,
                            )
                            generated_text = message.choices[0].message.content.lower().strip()
                            break
                        except Exception:
                            continue
                    else:
                        return False, "All AI models failed for validation"
                else:
                    raise

            is_valid = generated_text.startswith("yes")
            reason = generated_text.split('\n')[0] if '\n' in generated_text else generated_text

            logger.info(f"Word validation for '{word}': {is_valid}")
            return is_valid, reason

        except Exception as e:
            logger.error(f"Error validating word with Groq: {e}")
            return False, f"Validation error: {str(e)}"

