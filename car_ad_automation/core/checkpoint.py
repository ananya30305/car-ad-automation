"""Checkpoint system for resumable processing with stage-level tracking."""

import json
from pathlib import Path
from typing import Optional, List
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
            },
            'stages': {
                'normalize': {'status': 'pending', 'completed_ids': [], 'started_at': None, 'completed_at': None},
                'validate': {'status': 'pending', 'completed_ids': [], 'started_at': None, 'completed_at': None},
                'deduplicate': {'status': 'pending', 'completed_ids': [], 'started_at': None, 'completed_at': None},
                'descriptions': {'status': 'pending', 'completed_ids': [], 'started_at': None, 'completed_at': None},
                'images': {'status': 'pending', 'completed_ids': [], 'started_at': None, 'completed_at': None},
                'post_ads': {'status': 'pending', 'completed_ids': [], 'started_at': None, 'completed_at': None},
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
        # Reset stage statuses
        for stage in self.data['stages']:
            self.data['stages'][stage]['status'] = 'pending'
            self.data['stages'][stage]['completed_ids'] = []
            self.data['stages'][stage]['started_at'] = None
            self.data['stages'][stage]['completed_at'] = None
        self.save()
    
    # ============================================================
    # STAGE-LEVEL CHECKPOINTING
    # ============================================================
    
    def mark_stage_start(self, stage_name: str) -> None:
        """
        Mark a stage as started.
        
        Args:
            stage_name: Name of the stage
        """
        if stage_name in self.data['stages']:
            self.data['stages'][stage_name]['status'] = 'in_progress'
            self.data['stages'][stage_name]['started_at'] = datetime.now().isoformat()
            self.save()
    
    def mark_stage_complete(self, stage_name: str, completed_ids: List[str]) -> None:
        """
        Mark a stage as completed with the IDs that passed through it.
        
        Args:
            stage_name: Name of the stage
            completed_ids: List of record IDs that completed this stage
        """
        if stage_name in self.data['stages']:
            self.data['stages'][stage_name]['status'] = 'completed'
            self.data['stages'][stage_name]['completed_ids'] = completed_ids
            self.data['stages'][stage_name]['completed_at'] = datetime.now().isoformat()
            # Also update global processed_ids for resume functionality
            for record_id in completed_ids:
                if record_id not in self.data['processed_ids']:
                    self.data['processed_ids'].append(record_id)
            self.save()
    
    def get_stage_status(self, stage_name: str) -> dict:
        """
        Get status of a specific stage.
        
        Args:
            stage_name: Name of the stage
            
        Returns:
            Stage status dictionary
        """
        return self.data['stages'].get(stage_name, {})
    
    def get_completed_stage_ids(self, stage_name: str) -> List[str]:
        """
        Get IDs of records that completed a specific stage.
        
        Args:
            stage_name: Name of the stage
            
        Returns:
            List of record IDs
        """
        return self.data['stages'].get(stage_name, {}).get('completed_ids', [])
    
    def get_processed_ids(self) -> List[str]:
        """
        Get all processed record IDs (for backward compatibility and resume).
        
        Returns:
            List of all processed record IDs
        """
        return self.data.get('processed_ids', [])
    
    def get_remaining_records(self, all_records: List[dict], id_func) -> List[dict]:
        """
        Filter out records that have already completed the pipeline.
        
        Args:
            all_records: All records in the batch
            id_func: Function to extract ID from record
            
        Returns:
            Records that haven't been fully processed
        """
        # Check if all stages are completed
        all_stages_completed = all(
            self.data['stages'][s]['status'] == 'completed' 
            for s in self.data['stages']
        )
        
        if all_stages_completed:
            # All stages done, check individual record completion
            processed = set(self.get_processed_ids())
            return [r for r in all_records if id_func(r) not in processed]
        
        # Pipeline was interrupted mid-way, find where to resume
        # Get the last completed stage
        last_completed_stage = None
        for stage in ['normalize', 'validate', 'deduplicate', 'descriptions', 'images', 'post_ads']:
            if self.data['stages'][stage]['status'] == 'completed':
                last_completed_stage = stage
            else:
                break
        
        if last_completed_stage is None:
            # No stages completed, start from beginning
            return all_records
        
        # Get IDs that completed the last stage
        completed_ids = set(self.get_completed_stage_ids(last_completed_stage))
        
        # Return records that haven't completed the last stage
        return [r for r in all_records if id_func(r) not in completed_ids]
    
    # ============================================================
    # RECORD-LEVEL CHECKPOINTING (BACKWARD COMPATIBLE)
    # ============================================================
    
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
    
    def clear(self) -> None:
        """Clear checkpoint (for new run after successful completion)."""
        self.data = self._new_checkpoint()
        self.save()
    
    def reset(self) -> None:
        """Reset checkpoint (for new run)."""
        self.data = self._new_checkpoint()
        self.save()
