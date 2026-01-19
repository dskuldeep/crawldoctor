"""AI crawler detection service."""
import re
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
import structlog

logger = structlog.get_logger()


class CrawlerDetectionResult:
    """Result of crawler detection analysis."""
    
    def __init__(
        self,
        is_crawler: bool,
        crawler_name: Optional[str] = None,
        confidence_score: float = 0.0,
        detection_method: str = "unknown",
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.is_crawler = is_crawler
        self.crawler_name = crawler_name
        self.confidence_score = confidence_score
        self.detection_method = detection_method
        self.metadata = metadata or {}


class CrawlerDetectionService:
    """Service for detecting AI crawlers and bots."""
    
    def __init__(self):
        # Known AI crawler patterns
        self.ai_crawler_patterns = {
            # OpenAI/ChatGPT
            "GPTBot": {
                "pattern": r"GPTBot",
                "confidence": 0.95,
                "company": "OpenAI",
                "description": "OpenAI's web crawler for ChatGPT"
            },
            "ChatGPT-User": {
                "pattern": r"ChatGPT-User",
                "confidence": 0.90,
                "company": "OpenAI", 
                "description": "ChatGPT user agent"
            },
            "OpenAI": {
                "pattern": r"OpenAI",
                "confidence": 0.85,
                "company": "OpenAI",
                "description": "OpenAI crawler"
            },
            
            # Anthropic/Claude
            "ClaudeBot": {
                "pattern": r"ClaudeBot",
                "confidence": 0.95,
                "company": "Anthropic",
                "description": "Anthropic's Claude web crawler"
            },
            "Claude-Web": {
                "pattern": r"Claude-Web",
                "confidence": 0.90,
                "company": "Anthropic",
                "description": "Claude web interface"
            },
            "Anthropic": {
                "pattern": r"Anthropic",
                "confidence": 0.85,
                "company": "Anthropic",
                "description": "Anthropic crawler"
            },
            
            # Google AI
            "Google-Extended": {
                "pattern": r"Google-Extended",
                "confidence": 0.95,
                "company": "Google",
                "description": "Google's AI training crawler"
            },
            "GoogleBot": {
                "pattern": r"Googlebot",
                "confidence": 0.80,
                "company": "Google",
                "description": "Google's main crawler"
            },
            
            # Perplexity
            "PerplexityBot": {
                "pattern": r"PerplexityBot",
                "confidence": 0.95,
                "company": "Perplexity",
                "description": "Perplexity AI crawler"
            },
            "Perplexity": {
                "pattern": r"Perplexity",
                "confidence": 0.85,
                "company": "Perplexity",
                "description": "Perplexity crawler"
            },
            
            # Microsoft
            "BingBot": {
                "pattern": r"bingbot",
                "confidence": 0.80,
                "company": "Microsoft",
                "description": "Microsoft Bing crawler"
            },
            "EdgeGPT": {
                "pattern": r"EdgeGPT",
                "confidence": 0.85,
                "company": "Microsoft",
                "description": "Microsoft Edge AI crawler"
            },
            
            # Other AI companies
            "CCBot": {
                "pattern": r"CCBot",
                "confidence": 0.75,
                "company": "Common Crawl",
                "description": "Common Crawl bot"
            },
            "Bytespider": {
                "pattern": r"Bytespider",
                "confidence": 0.70,
                "company": "ByteDance",
                "description": "ByteDance crawler"
            }
        }
        
        # General bot patterns
        self.general_bot_patterns = [
            r"bot",
            r"crawler", 
            r"spider",
            r"scraper",
            r"robot",
            r"crawling"
        ]
    
    def detect_crawler(
        self,
        user_agent: str,
        ip_address: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        db: Optional[Session] = None
    ) -> CrawlerDetectionResult:
        """
        Detect if a request is from an AI crawler or bot.
        
        Args:
            user_agent: HTTP User-Agent string
            ip_address: Client IP address (optional)
            headers: HTTP headers (optional)
            db: Database session (optional)
            
        Returns:
            CrawlerDetectionResult with detection information
        """
        if not user_agent:
            return CrawlerDetectionResult(is_crawler=False, confidence_score=0.0)
        
        user_agent_lower = user_agent.lower()
        
        # Check for known AI crawlers first
        for crawler_name, pattern_info in self.ai_crawler_patterns.items():
            if re.search(pattern_info["pattern"], user_agent, re.IGNORECASE):
                return CrawlerDetectionResult(
                    is_crawler=True,
                    crawler_name=crawler_name,
                    confidence_score=pattern_info["confidence"],
                    detection_method="pattern_match",
                    metadata={
                        "company": pattern_info["company"],
                        "description": pattern_info["description"]
                    }
                )
        
        # Check for general bot patterns
        for pattern in self.general_bot_patterns:
            if re.search(pattern, user_agent_lower):
                return CrawlerDetectionResult(
                    is_crawler=True,
                    crawler_name="Unknown Bot",
                    confidence_score=0.60,
                    detection_method="general_pattern",
                    metadata={"pattern": pattern}
                )
        
        # Check for suspicious patterns
        suspicious_patterns = [
            r"python",
            r"curl",
            r"wget", 
            r"scrapy",
            r"selenium",
            r"headless",
            r"phantomjs"
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, user_agent_lower):
                return CrawlerDetectionResult(
                    is_crawler=True,
                    crawler_name="Suspicious Bot",
                    confidence_score=0.50,
                    detection_method="suspicious_pattern",
                    metadata={"pattern": pattern}
                )
        
        # Check for missing or suspicious user agents
        if not user_agent or user_agent == "" or len(user_agent) < 10:
            return CrawlerDetectionResult(
                is_crawler=True,
                crawler_name="Empty User Agent",
                confidence_score=0.40,
                detection_method="empty_user_agent"
            )
        
        # Check for browser-like patterns (likely human)
        browser_patterns = [
            r"mozilla",
            r"chrome",
            r"safari", 
            r"firefox",
            r"edge",
            r"opera"
        ]
        
        browser_matches = 0
        for pattern in browser_patterns:
            if re.search(pattern, user_agent_lower):
                browser_matches += 1
        
        if browser_matches >= 2:
            return CrawlerDetectionResult(
                is_crawler=False,
                crawler_name=None,
                confidence_score=0.80,
                detection_method="browser_pattern"
            )
        
        # Default to unknown
        return CrawlerDetectionResult(
            is_crawler=False,
            crawler_name=None,
            confidence_score=0.30,
            detection_method="unknown"
        )
    
    def get_crawler_info(self, crawler_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific crawler."""
        return self.ai_crawler_patterns.get(crawler_name)
    
    def get_all_crawlers(self) -> List[Dict[str, Any]]:
        """Get list of all known crawlers."""
        return [
            {
                "name": name,
                **info
            }
            for name, info in self.ai_crawler_patterns.items()
        ]
    
    def is_ai_crawler(self, user_agent: str) -> bool:
        """Quick check if user agent is from an AI crawler."""
        result = self.detect_crawler(user_agent)
        return result.is_crawler and result.confidence_score > 0.7
    
    def get_crawler_company(self, user_agent: str) -> Optional[str]:
        """Get the company name for a crawler user agent."""
        result = self.detect_crawler(user_agent)
        if result.metadata and "company" in result.metadata:
            return result.metadata["company"]
        return None
