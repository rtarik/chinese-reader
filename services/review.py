from dataclasses import dataclass
from typing import List, Optional
import time
from db import SavedWord, ReviewStats, update_review_stats, get_words_for_review

@dataclass
class ReviewSession:
    words: List[SavedWord]
    current_index: int = 0
    total_words: int = 0
    
    @property
    def current_word(self) -> Optional[SavedWord]:
        if self.current_index < len(self.words):
            return self.words[self.current_index]
        return None
    
    @property
    def is_complete(self) -> bool:
        return self.current_index >= len(self.words)

def calculate_next_review(correct: bool, stats: Optional[ReviewStats]) -> tuple[float, float, float]:
    """Calculate the next review time using a modified SuperMemo 2 algorithm.
    Returns (next_review_timestamp, new_interval, new_ease_factor)"""
    current_time = time.time()
    
    # Default values for new words
    ease_factor = stats.ease_factor if stats else 2.5
    interval = stats.interval if stats else 1.0
    
    if correct:
        if interval == 1.0:  # First review
            interval = 1.0
        elif interval == 1:  # Second review
            interval = 6.0
        else:
            interval *= ease_factor
        
        # Increase ease factor for correct answers (max 2.5)
        ease_factor = min(ease_factor + 0.1, 2.5)
    else:
        # Reset interval and decrease ease factor for incorrect answers (min 1.3)
        interval = 1.0
        ease_factor = max(1.3, ease_factor - 0.2)
    
    # Convert interval from days to seconds and add to current time
    next_review = current_time + (interval * 86400)  # 86400 seconds = 1 day
    
    return next_review, interval, ease_factor

# Global review session state
current_session: Optional[ReviewSession] = None

def start_review_session(limit: int = 10) -> Optional[ReviewSession]:
    """Start a new review session"""
    global current_session
    words = get_words_for_review(limit)
    if not words:
        return None
    
    current_session = ReviewSession(words=words, total_words=len(words))
    return current_session

def end_review_session() -> None:
    """End the current review session"""
    global current_session
    current_session = None

def get_current_session() -> Optional[ReviewSession]:
    """Get the current review session"""
    return current_session

def advance_session() -> bool:
    """Advance to the next word in the session.
    Returns True if there are more words, False if session is complete."""
    global current_session
    if not current_session:
        return False
        
    current_session.current_index += 1
    return not current_session.is_complete 