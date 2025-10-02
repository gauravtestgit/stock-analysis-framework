from dataclasses import dataclass
from typing import List

@dataclass
class QualityScore:
    score: int
    max_score: int = 100
    grade: str = ""
    data_quality: str = "Medium"
    missing_data_penalty: int = 0
    strengths: List[str] = None
    weaknesses: List[str] = None
    
    def __post_init__(self):
        if self.strengths is None:
            self.strengths = []
        if self.weaknesses is None:
            self.weaknesses = []
        
        # Auto-calculate grade
        if self.score >= 80:
            self.grade = 'A'
        elif self.score >= 60:
            self.grade = 'B'
        elif self.score >= 40:
            self.grade = 'C'
        else:
            self.grade = 'D'