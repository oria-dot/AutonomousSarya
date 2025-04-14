#!/usr/bin/env python3
"""
Unified Intelligence Module for SARYA.
Provides cognitive processing, knowledge management, and decision-making capabilities.
"""
import os
import json
import logging
import datetime
from typing import Dict, List, Any, Optional, Tuple

from core.base_module import BaseModule

logger = logging.getLogger(__name__)

class IntelligenceModule(BaseModule):
    """
    Core intelligence module that provides reasoning, decision-making, and knowledge management.
    Acts as a central cognitive system for SARYA.
    """
    
    def __init__(self, module_id=None):
        """Initialize the IntelligenceModule."""
        super().__init__(name="IntelligenceModule")
        self.knowledge_base = {}
        self.reasoning_models = {}
        self.decision_history = []
        self.knowledge_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "knowledge_base.json")
        
    def _start(self) -> bool:
        """Start the intelligence module."""
        logger.info("Starting intelligence module")
        return True
        
    def _stop(self) -> bool:
        """Stop the intelligence module."""
        logger.info("Stopping intelligence module")
        # Save any unsaved knowledge
        self._save_knowledge_base()
        return True
    
    def _initialize(self) -> bool:
        """
        Initialize the intelligence module.
        
        Returns:
            bool: True if initialization was successful
        """
        try:
            # Load knowledge base
            self._load_knowledge_base()
            
            # Initialize reasoning models
            self._initialize_reasoning_models()
            
            logger.info("Intelligence module initialized")
            return True
        except Exception as e:
            logger.error(f"Error initializing intelligence module: {e}")
            return False
    
    def _load_knowledge_base(self) -> bool:
        """
        Load knowledge base from file.
        
        Returns:
            bool: True if loading was successful
        """
        try:
            if os.path.exists(self.knowledge_path):
                with open(self.knowledge_path, 'r') as f:
                    self.knowledge_base = json.load(f)
                logger.info(f"Loaded knowledge base with {len(self.knowledge_base)} concepts")
            else:
                logger.warning(f"Knowledge base file not found at {self.knowledge_path}, initializing empty knowledge base")
                self.knowledge_base = {
                    "concepts": {},
                    "relationships": [],
                    "metadata": {
                        "created_at": datetime.datetime.utcnow().isoformat(),
                        "updated_at": datetime.datetime.utcnow().isoformat(),
                        "version": "1.0"
                    }
                }
                # Save the initial knowledge base
                self._save_knowledge_base()
            return True
        except Exception as e:
            logger.error(f"Error loading knowledge base: {e}")
            self.knowledge_base = {"concepts": {}, "relationships": [], "metadata": {}}
            return False
    
    def _save_knowledge_base(self) -> bool:
        """
        Save knowledge base to file.
        
        Returns:
            bool: True if saving was successful
        """
        try:
            # Update metadata
            if "metadata" not in self.knowledge_base:
                self.knowledge_base["metadata"] = {}
            
            self.knowledge_base["metadata"]["updated_at"] = datetime.datetime.utcnow().isoformat()
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.knowledge_path), exist_ok=True)
            
            with open(self.knowledge_path, 'w') as f:
                json.dump(self.knowledge_base, f, indent=2)
            
            logger.info(f"Saved knowledge base to {self.knowledge_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving knowledge base: {e}")
            return False
    
    def _initialize_reasoning_models(self) -> bool:
        """
        Initialize reasoning models.
        
        Returns:
            bool: True if initialization was successful
        """
        try:
            # Define the basic reasoning models
            self.reasoning_models = {
                "deductive": self._deductive_reasoning,
                "inductive": self._inductive_reasoning,
                "abductive": self._abductive_reasoning,
                "analogical": self._analogical_reasoning
            }
            logger.info(f"Initialized {len(self.reasoning_models)} reasoning models")
            return True
        except Exception as e:
            logger.error(f"Error initializing reasoning models: {e}")
            return False
    
    def add_knowledge(self, concept_id: str, concept_data: Dict[str, Any]) -> bool:
        """
        Add or update a concept in the knowledge base.
        
        Args:
            concept_id: Unique identifier for the concept
            concept_data: Data associated with the concept
            
        Returns:
            bool: True if the concept was added or updated successfully
        """
        try:
            if "concepts" not in self.knowledge_base:
                self.knowledge_base["concepts"] = {}
            
            # Add or update concept
            self.knowledge_base["concepts"][concept_id] = concept_data
            
            # Save changes
            self._save_knowledge_base()
            logger.info(f"Added/updated concept {concept_id} in knowledge base")
            return True
        except Exception as e:
            logger.error(f"Error adding concept {concept_id} to knowledge base: {e}")
            return False
    
    def get_knowledge(self, concept_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a concept from the knowledge base.
        
        Args:
            concept_id: Unique identifier for the concept
            
        Returns:
            Dict or None: The concept data if found, None otherwise
        """
        try:
            if "concepts" not in self.knowledge_base:
                return {}
            
            return self.knowledge_base["concepts"].get(concept_id, {})
        except Exception as e:
            logger.error(f"Error getting concept {concept_id} from knowledge base: {e}")
            return {}
    
    def add_relationship(self, source_id: str, target_id: str, relationship_type: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Add a relationship between two concepts.
        
        Args:
            source_id: Source concept ID
            target_id: Target concept ID
            relationship_type: Type of relationship
            metadata: Additional metadata about the relationship
            
        Returns:
            bool: True if the relationship was added successfully
        """
        try:
            if "relationships" not in self.knowledge_base:
                self.knowledge_base["relationships"] = []
            
            # Create relationship object
            relationship = {
                "source": source_id,
                "target": target_id,
                "type": relationship_type,
                "metadata": metadata or {},
                "created_at": datetime.datetime.utcnow().isoformat()
            }
            
            # Add relationship
            self.knowledge_base["relationships"].append(relationship)
            
            # Save changes
            self._save_knowledge_base()
            logger.info(f"Added relationship between {source_id} and {target_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding relationship: {e}")
            return False
    
    def make_decision(self, context: Dict[str, Any], options: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Make a decision based on context and available options.
        
        Args:
            context: Context information for the decision
            options: List of available options
            
        Returns:
            Dict: The selected option with reasoning
        """
        try:
            if not options:
                logger.warning("No options provided for decision making")
                return {"error": "No options provided"}
            
            # Simple scoring mechanism for demonstration
            scored_options = []
            for option in options:
                score = self._evaluate_option(option, context)
                scored_options.append((option, score))
            
            # Sort by score (descending)
            scored_options.sort(key=lambda x: x[1], reverse=True)
            
            # Select highest-scoring option
            selected_option = scored_options[0][0]
            
            # Record decision for history
            decision_record = {
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "context": context,
                "options": options,
                "selected": selected_option,
                "reasoning": f"Selected option with highest score: {scored_options[0][1]}"
            }
            self.decision_history.append(decision_record)
            
            # Return selected option with reasoning
            return {
                "selected": selected_option,
                "reasoning": decision_record["reasoning"],
                "confidence": scored_options[0][1] / 100  # Normalize to 0-1 range
            }
        except Exception as e:
            logger.error(f"Error making decision: {e}")
            return {"error": str(e)}
    
    def _evaluate_option(self, option: Dict[str, Any], context: Dict[str, Any]) -> float:
        """
        Evaluate an option based on context.
        
        Args:
            option: Option to evaluate
            context: Context for evaluation
            
        Returns:
            float: Score for the option (0-100)
        """
        # In a real implementation, this would be a more sophisticated
        # evaluation using various reasoning methods
        
        # For now, use a simple scoring mechanism
        score = 50.0  # Default middle score
        
        # Adjust score based on priority if available
        if "priority" in option:
            score += option["priority"] * 10
        
        # Adjust score based on relevance to context
        if "tags" in option and "tags" in context:
            matching_tags = set(option.get("tags", [])) & set(context.get("tags", []))
            score += len(matching_tags) * 5
        
        # Cap score at 0-100
        return max(0, min(100, score))
    
    def reason(self, query: Dict[str, Any], reasoning_type: str = "deductive") -> Dict[str, Any]:
        """
        Apply reasoning to a query.
        
        Args:
            query: The query to reason about
            reasoning_type: Type of reasoning to apply
            
        Returns:
            Dict: Result of reasoning
        """
        try:
            if reasoning_type not in self.reasoning_models:
                logger.warning(f"Unknown reasoning type: {reasoning_type}, falling back to deductive")
                reasoning_type = "deductive"
            
            # Apply selected reasoning model
            reasoning_function = self.reasoning_models[reasoning_type]
            result = reasoning_function(query)
            
            return {
                "query": query,
                "reasoning_type": reasoning_type,
                "result": result,
                "timestamp": datetime.datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error applying {reasoning_type} reasoning: {e}")
            return {"error": str(e)}
    
    def _deductive_reasoning(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply deductive reasoning (from general to specific).
        
        Args:
            query: Query containing premises and potentially a conclusion
            
        Returns:
            Dict: Result of deductive reasoning
        """
        # Simplified implementation
        premises = query.get("premises", [])
        conclusion = query.get("conclusion", {})
        
        # In a real implementation, this would apply formal logic rules
        # For now, simply check if conclusion is compatible with all premises
        valid = len(premises) > 0
        explanation = "Deduction based on provided premises"
        
        return {
            "valid": valid,
            "explanation": explanation
        }
    
    def _inductive_reasoning(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply inductive reasoning (from specific to general).
        
        Args:
            query: Query containing observations and potentially a hypothesis
            
        Returns:
            Dict: Result of inductive reasoning
        """
        # Simplified implementation
        observations = query.get("observations", [])
        hypothesis = query.get("hypothesis", {})
        
        # In a real implementation, this would identify patterns in observations
        # For now, return a probability based on number of observations
        probability = min(len(observations) * 0.1, 0.9) if observations else 0
        explanation = "Induction based on provided observations"
        
        return {
            "probability": probability,
            "explanation": explanation
        }
    
    def _abductive_reasoning(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply abductive reasoning (inference to best explanation).
        
        Args:
            query: Query containing observations and potential explanations
            
        Returns:
            Dict: Result of abductive reasoning with best explanation
        """
        # Simplified implementation
        observations = query.get("observations", [])
        explanations = query.get("explanations", [])
        
        # In a real implementation, this would evaluate explanations against observations
        # For now, select the first explanation if available
        best_explanation = explanations[0] if explanations else {}
        confidence = 0.5 if explanations else 0
        explanation = "Abduction to find best explanation for observations"
        
        return {
            "best_explanation": best_explanation,
            "confidence": confidence,
            "reasoning": explanation
        }
    
    def _analogical_reasoning(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply analogical reasoning (mapping from source to target domain).
        
        Args:
            query: Query containing source and target domains
            
        Returns:
            Dict: Result of analogical reasoning with mappings
        """
        # Simplified implementation
        source = query.get("source", {})
        target = query.get("target", {})
        
        # In a real implementation, this would identify structural mappings
        # For now, return an empty mapping
        mappings = []
        confidence = 0.4 if source and target else 0
        explanation = "Analogical mapping between source and target domains"
        
        return {
            "mappings": mappings,
            "confidence": confidence,
            "explanation": explanation
        }
    
    def get_decision_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent decision history.
        
        Args:
            limit: Maximum number of decisions to return
            
        Returns:
            List: Recent decisions
        """
        # Return most recent decisions first
        return self.decision_history[-limit:][::-1] if self.decision_history else []

# Standalone function to test the module
def test_intelligence_module():
    """Test the intelligence module."""
    import logging
    logging.basicConfig(level=logging.INFO)
    
    intelligence = IntelligenceModule()
    intelligence._initialize()
    
    # Add some knowledge
    intelligence.add_knowledge("concept1", {
        "name": "Test Concept",
        "description": "A test concept for demonstration",
        "tags": ["test", "demonstration"]
    })
    
    # Add a relationship
    intelligence.add_relationship("concept1", "concept2", "related_to", {"strength": 0.8})
    
    # Make a decision
    decision = intelligence.make_decision(
        context={"tags": ["test", "important"]},
        options=[
            {"id": "option1", "name": "Option 1", "tags": ["test"], "priority": 2},
            {"id": "option2", "name": "Option 2", "tags": ["important"], "priority": 1}
        ]
    )
    
    print("Decision:", decision)
    
    # Test reasoning
    reasoning = intelligence.reason(
        query={
            "premises": [
                "All humans are mortal",
                "Socrates is human"
            ],
            "conclusion": "Socrates is mortal"
        }
    )
    
    print("Reasoning:", reasoning)
    
    return intelligence

if __name__ == "__main__":
    test_intelligence_module()