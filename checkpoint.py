"""Checkpoint system for resumable processing."""

import json
from pathlib import Path
from typing import Optional
from datetime import datetime


class Checkpoint:
    """Manages processing checkpoints for resumable workflows."""
    
    def __init__(self, checkpoint_file: Path):
        """
        Initialize checkpoint.
        
        Args:
            checkpoint_file: Path to checkpoint file
        """
        self.checkpoint_file = Path(checkpoint_file)
        self.data = self._load()
    
    def _load(self) -> dict:
        """Load checkpoint from file."""
        if self.checkpoint_file.exists():
            try:
                return json.loads(self.checkpoint_file.read_text(encoding='utf-8'))
            except (json.JSONDecodeError, IOError):
                return self._new_checkpoint()
        return self._new_checkpoint()
    
    def _new_checkpoint(self) -> dict:
        """Create new checkpoint structure."""
        return {
            'last_processed_index': -1,
            'processed_ids': [],
            'successful_ids': [],
            'failed_ids': [],
            'started_at': None,
            'last_updated': None,
            'total_records': 0,
            'summary': {
                'total_processed': 0,
                'total_successful': 0,
                'total_failed': 0,
                'total_duplicates': 0,
            }
        }
    
    def save(self) -> None:
        """Save checkpoint to file."""
        self.data['last_updated'] = datetime.now().isoformat()
        
        # Ensure directory exists
        self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Write atomically
        temp_file = self.checkpoint_file.with_suffix('.tmp')
        temp_file.write_text(json.dumps(self.data, indent=2), encoding='utf-8')
        temp_file.replace(self.checkpoint_file)
    
    def initialize(self, total_records: int) -> None:
        """
        Initialize checkpoint for new batch.
        
        Args:
            total_records: Total number of records to process
        """
        self.data['started_at'] = datetime.now().isoformat()
        self.data['total_records'] = total_records
        self.save()
    
    def mark_processed(self, record_id: str, index: int, success: bool = True) -> None:
        """
        Mark record as processed.
        
        Args:
            record_id: ID of record
            index: Index in batch
            success: Whether processing was successful
        """
        self.data['last_processed_index'] = index
        
        if record_id not in self.data['processed_ids']:
            self.data['processed_ids'].append(record_id)
        
        if success:
            if record_id not in self.data['successful_ids']:
                self.data['successful_ids'].append(record_id)
        else:
            if record_id not in self.data['failed_ids']:
                self.data['failed_ids'].append(record_id)
        
        self.save()
    
    def mark_duplicate(self, record_id: str) -> None:
        """
        Mark record as duplicate.
        
        Args:
            record_id: ID of record
        """
        self.data['summary']['total_duplicates'] += 1
        self.save()
    
    def should_skip(self, record_id: str) -> bool:
        """
        Check if record was already processed.
        
        Args:
            record_id: ID of record
            
        Returns:
            True if already processed
        """
        return record_id in self.data['processed_ids']
    
    def get_last_index(self) -> int:
        """
        Get index of last processed record.
        
        Returns:
            Index, or -1 if none processed
        """
        return self.data['last_processed_index']
    
    def get_summary(self) -> dict:
        """
        Get processing summary.
        
        Returns:
            Summary dictionary
        """
        return {
            'total_records': self.data['total_records'],
            'processed': len(self.data['processed_ids']),
            'successful': len(self.data['successful_ids']),
            'failed': len(self.data['failed_ids']),
            'duplicates': self.data['summary'].get('total_duplicates', 0),
            'pending': self.data['total_records'] - len(self.data['processed_ids']),
        }
    
    def reset(self) -> None:
        """Reset checkpoint (for new run)."""
        self.data = self._new_checkpoint()
        self.save()
