import time
from typing import List, Optional
from .models import db, saved_words, review_stats, SavedWord, ReviewStats

def save_word(word_data: dict) -> SavedWord:
    """Save a word to the database"""
    saved_words.insert({
        'word': word_data['word'],
        'simplified': word_data['simplified'],
        'traditional': word_data['traditional'],
        'pinyin': word_data['pinyin'],
        'definitions': word_data['definitions'],
        'timestamp': time.time()
    })
    return SavedWord(**word_data, timestamp=time.time())

def delete_word(word: str) -> None:
    """Delete a word and its review stats from the database"""
    if word in saved_words:
        saved_words.delete(word)
    if word in review_stats:
        review_stats.delete(word)

def get_all_saved_words(order_by: str = '-timestamp') -> List[SavedWord]:
    """Get all saved words, optionally ordered by a field"""
    words = saved_words(order_by=order_by)
    return [SavedWord(**word) for word in words]

def is_word_saved(word: str) -> bool:
    """Check if a word is saved"""
    return word in saved_words

def update_review_stats(word: str, is_correct: bool, next_review: float, 
                       interval: float, ease_factor: float) -> ReviewStats:
    """Update review statistics for a word"""
    stats = review_stats[word] if word in review_stats else {}
    review_data = {
        'word': word,
        'correct_count': stats.get('correct_count', 0) + (1 if is_correct else 0),
        'incorrect_count': stats.get('incorrect_count', 0) + (0 if is_correct else 1),
        'last_reviewed': time.time(),
        'next_review': next_review,
        'ease_factor': ease_factor,
        'interval': interval
    }
    
    if word in review_stats:
        review_stats.update(review_data, word)
    else:
        review_stats.insert(review_data)
    
    return ReviewStats(**review_data)

def get_review_stats(word: str) -> Optional[ReviewStats]:
    """Get review statistics for a word"""
    if word in review_stats:
        return ReviewStats(**review_stats[word])
    return None

def get_words_for_review(limit: int = 10) -> List[SavedWord]:
    """Get words that are due for review"""
    current_time = time.time()
    
    # Get all saved words
    all_saved_words = saved_words()
    if not all_saved_words:
        return []
    
    # Get words with review stats
    reviewed_words = {r['word']: r for r in review_stats()}
    
    # Separate words into categories
    new_words = []
    due_words = []
    future_words = []
    
    for word in all_saved_words:
        word_id = word['word']
        if word_id not in reviewed_words:
            new_words.append(SavedWord(**word))
        else:
            stats = reviewed_words[word_id]
            if stats['next_review'] <= current_time:
                # Calculate priority based on how overdue and incorrect count
                overdue_days = (current_time - stats['next_review']) / 86400
                priority = overdue_days + stats['incorrect_count']
                due_words.append((priority, SavedWord(**word)))
            else:
                # For words not due yet, prioritize by incorrect count and shorter intervals
                priority = stats['incorrect_count'] - (stats['next_review'] - current_time) / 86400
                future_words.append((priority, SavedWord(**word)))
    
    # Sort due and future words by priority (highest first)
    due_words.sort(reverse=True, key=lambda x: x[0])
    future_words.sort(reverse=True, key=lambda x: x[0])
    
    # Extract just the words from the priority tuples
    due_words = [word for _, word in due_words]
    future_words = [word for _, word in future_words]
    
    # Combine all words in priority order
    review_words = new_words + due_words + future_words
    
    # Return all words if <= limit, otherwise return up to limit
    return review_words if len(review_words) <= limit else review_words[:limit] 