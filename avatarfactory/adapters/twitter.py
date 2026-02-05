"""
Twitter/X platform adapter.
"""

from typing import Any, Dict

from avatarfactory.adapters.base import BasePlatformAdapter
from avatarfactory.models.schemas import Content, PlatformType


class TwitterAdapter(BasePlatformAdapter):
    """Twitter/X-specific adapter"""

    def __init__(self):
        super().__init__(PlatformType.TWITTER)

    def get_content_guidelines(self) -> Dict[str, Any]:
        """Get Twitter content guidelines"""
        return {
            "format": "thread",
            "max_length_per_tweet": 280,
            "thread_length": {"min": 3, "max": 15, "optimal": 7},
            "tone": "Concise, punchy, conversational",
            "structure": "Hook → Value → CTA",
            "content_types": [
                "Thread (multi-tweet story/tutorial)",
                "Hot take/opinion",
                "Quick tip",
                "Poll/question",
                "Quote tweet with commentary",
            ],
            "engagement_tactics": [
                "Start with a hook tweet",
                "Use line breaks for readability",
                "Add relevant hashtags (1-2 max)",
                "End with CTA (like/retweet/follow)",
                "Tag relevant people/brands (sparingly)",
            ],
            "avoid": [
                "Walls of text",
                "Too many hashtags",
                "Excessive self-promotion",
                "Engagement bait",
                "Controversial hot takes without substance",
            ],
        }

    def validate_content(self, content: Content) -> Dict[str, Any]:
        """Validate content for Twitter"""
        issues = []
        warnings = []

        guidelines = self.get_content_guidelines()

        # Check if content needs to be split into thread
        total_length = len(content.body)
        if total_length > guidelines["max_length_per_tweet"]:
            tweet_count = (total_length // guidelines["max_length_per_tweet"]) + 1
            if tweet_count > guidelines["thread_length"]["max"]:
                warnings.append(
                    f"Content very long ({tweet_count} tweets), consider condensing"
                )

        # Check hashtag count
        hashtag_count = len(content.tags)
        if hashtag_count > 2:
            warnings.append("Too many hashtags for Twitter (max 1-2 recommended)")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "score": 100 - (len(issues) * 20 + len(warnings) * 5),
        }

    def format_for_export(self, content: Content) -> Dict[str, Any]:
        """Format content for Twitter thread"""
        # Split content into tweets
        tweets = self._split_into_tweets(content.body)

        # Add numbering to thread
        if len(tweets) > 1:
            numbered_tweets = [f"{i+1}/{len(tweets)}\n\n{tweet}" for i, tweet in enumerate(tweets)]
        else:
            numbered_tweets = tweets

        # Add hashtags to last tweet
        if content.tags:
            hashtags = " ".join([f"#{tag}" for tag in content.tags[:2]])
            numbered_tweets[-1] = f"{numbered_tweets[-1]}\n\n{hashtags}"

        return {
            "platform": "twitter",
            "thread": numbered_tweets,
            "metadata": {
                "content_id": content.id,
                "pillar": content.pillar,
                "tweet_count": len(numbered_tweets),
                "posting_tips": [
                    "Post during peak hours for your audience",
                    "Engage with replies quickly",
                    "Pin the thread if it performs well",
                    "Consider adding images/GIFs to first tweet",
                ],
            },
        }

    def _split_into_tweets(self, text: str, max_length: int = 250) -> list[str]:
        """Split text into tweet-sized chunks"""
        tweets = []
        paragraphs = text.split("\n\n")

        current_tweet = ""
        for para in paragraphs:
            # If single paragraph is longer than max_length, split it by sentences/words
            if len(para) > max_length:
                # First, flush current tweet
                if current_tweet:
                    tweets.append(current_tweet.strip())
                    current_tweet = ""
                # Split long paragraph by sentences or words
                words = para.split()
                chunk = ""
                for word in words:
                    if len(chunk) + len(word) + 1 <= max_length:
                        chunk += (" " + word) if chunk else word
                    else:
                        if chunk:
                            tweets.append(chunk.strip())
                        chunk = word
                if chunk:
                    current_tweet = chunk
            elif len(current_tweet) + len(para) + 2 <= max_length:
                current_tweet += (para + "\n\n") if current_tweet else para
            else:
                if current_tweet:
                    tweets.append(current_tweet.strip())
                current_tweet = para

        if current_tweet:
            tweets.append(current_tweet.strip())

        return tweets

    def get_best_posting_times(self) -> list[str]:
        """Get best posting times for Twitter"""
        return [
            "8:00-10:00",
            "12:00-13:00",
            "17:00-18:00",
        ]

    def get_hashtag_strategy(self) -> Dict[str, Any]:
        """Get Twitter hashtag strategy"""
        return {
            "recommended_count": 1,
            "max_count": 2,
            "placement": "end_of_tweet",
            "guidelines": [
                "Use 1-2 highly relevant hashtags max",
                "Research trending hashtags in your niche",
                "Create a branded hashtag for series",
                "Avoid overused generic hashtags",
            ],
        }
