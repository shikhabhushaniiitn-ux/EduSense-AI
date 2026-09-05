"""
AI-Generated Learning Paths for EduSense AI.

Fulfills Assessment Requirement 15:
For broad topics, creates a structured, prerequisite-ordered learning path
(e.g., Machine Learning -> 1. Python Fundamentals -> 2. Math for ML ->
3. Data Processing -> 4. Supervised Learning -> etc.)
and generates an interactive Mermaid roadmap.
"""

import json
import re
from modules.ai_client import generate_text
from modules.style_dna import StyleDNA

# Built-in high-quality curriculum blueprints for instant load
PRESET_LEARNING_PATHS = {
    "Machine Learning": {
        "title": "Machine Learning: From Fundamentals to Neural Networks",
        "description": "A comprehensive end-to-end roadmap covering mathematical foundations, core algorithms, and deep neural architectures.",
        "modules": [
            {"order": 1, "title": "Python & NumPy Fundamentals", "description": "Vectorized computations, array slicing, and mathematical programming.", "duration": "1.5 hrs"},
            {"order": 2, "title": "Mathematics for ML", "description": "Linear algebra (matrices, vectors, eigenvalues) and multivariable calculus (gradients).", "duration": "2.0 hrs"},
            {"order": 3, "title": "Data Processing & Feature Engineering", "description": "Handling missing data, normalization, categorical encoding, train/test split.", "duration": "1.5 hrs"},
            {"order": 4, "title": "Supervised Learning: Regression", "description": "Linear, polynomial, and regularized regression (Ridge, Lasso) with MSE evaluation.", "duration": "2.0 hrs"},
            {"order": 5, "title": "Supervised Learning: Classification", "description": "Logistic regression, decision trees, support vector machines, and ROC-AUC curves.", "duration": "2.5 hrs"},
            {"order": 6, "title": "Unsupervised Learning", "description": "K-Means clustering, hierarchical clustering, and PCA dimensionality reduction.", "duration": "1.5 hrs"},
            {"order": 7, "title": "Model Evaluation & Hyperparameter Tuning", "description": "K-fold cross validation, bias-variance tradeoff, and grid search.", "duration": "1.5 hrs"},
            {"order": 8, "title": "Introduction to Neural Networks", "description": "Perceptrons, backpropagation, activation functions, and deep learning basics.", "duration": "3.0 hrs"}
        ]
    },
    "Classical Mechanics": {
        "title": "Classical Mechanics: Laws of Motion & Energy",
        "description": "Newtonian physics from foundational kinematics through momentum, work-energy theorem, and rotational dynamics.",
        "modules": [
            {"order": 1, "title": "1D & 2D Kinematics", "description": "Position, velocity, acceleration vectors, and projectile motion equations.", "duration": "1.5 hrs"},
            {"order": 2, "title": "Newton's First Law & Inertia", "description": "Inertial reference frames, balanced forces, and equilibrium.", "duration": "1.0 hr"},
            {"order": 3, "title": "Newton's Second Law (F = ma)", "description": "Net force, mass vs weight, free body diagrams, and friction.", "duration": "2.0 hrs"},
            {"order": 4, "title": "Newton's Third Law (Action-Reaction)", "description": "Force pairs, normal forces, and tension in connected bodies.", "duration": "1.5 hrs"},
            {"order": 5, "title": "Work, Energy & Power", "description": "Work-energy theorem, kinetic vs potential energy, and conservative forces.", "duration": "2.0 hrs"},
            {"order": 6, "title": "Linear Momentum & Collisions", "description": "Conservation of momentum, impulse, elastic and inelastic collisions.", "duration": "2.0 hrs"},
            {"order": 7, "title": "Circular Motion & Gravity", "description": "Centripetal acceleration, universal gravitation, and planetary orbits.", "duration": "2.0 hrs"}
        ]
    },
    "React & Frontend Engineering": {
        "title": "Modern React: From Components to Production Architecture",
        "description": "Component architecture, hooks, state management, and production-ready frontend workflows.",
        "modules": [
            {"order": 1, "title": "JavaScript ES6+ Essentials", "description": "Destructuring, spread operators, arrow functions, promises, and async/await.", "duration": "1.5 hrs"},
            {"order": 2, "title": "React Core & JSX Architecture", "description": "Virtual DOM, JSX syntax, functional components, and props passing.", "duration": "2.0 hrs"},
            {"order": 3, "title": "State Management with useState", "description": "Component state, immutability, lifting state up, and controlled inputs.", "duration": "2.0 hrs"},
            {"order": 4, "title": "Side Effects with useEffect", "description": "Component lifecycle, dependency arrays, cleanup functions, and API fetching.", "duration": "2.0 hrs"},
            {"order": 5, "title": "Advanced Hooks (useMemo, useCallback, useRef)", "description": "Performance optimization, DOM references, and stable callbacks.", "duration": "2.0 hrs"},
            {"order": 6, "title": "Global State with Context & Redux", "description": "Avoiding prop drilling, Context API, Redux Toolkit basics.", "duration": "2.5 hrs"},
            {"order": 7, "title": "Routing & Full Application Flow", "description": "React Router v6, protected routes, and production deployment.", "duration": "2.0 hrs"}
        ]
    }
}


def generate_learning_path(topic, level="Beginner"):
    """
    Generate or retrieve a structured learning path for a broad topic.
    If topic matches a preset, return it instantly; otherwise prompt AI.
    """
    topic_clean = topic.strip()
    for key, preset in PRESET_LEARNING_PATHS.items():
        if key.lower() in topic_clean.lower() or topic_clean.lower() in key.lower():
            return preset

    # Generate via AI
    prompt = f"""
You are an expert curriculum designer. Create a progressive, structured learning path for:
Topic: "{topic_clean}"
Learner Level: {level}

Return ONLY valid JSON (no markdown formatting, no code blocks):
{{
  "title": "concise curriculum title",
  "description": "1-2 sentence overview of what this roadmap achieves",
  "modules": [
    {{
      "order": 1,
      "title": "Module title",
      "description": "1-sentence summary of concepts taught",
      "duration": "e.g. 1.5 hrs"
    }},
    ... (between 5 and 8 sequential modules, arranged from foundational to advanced)
  ]
}}
"""
    try:
        raw = generate_text(prompt, max_tokens=1200, temperature=0.2)
        if raw:
            cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            data = json.loads(cleaned)
            if "modules" in data and len(data["modules"]) >= 3:
                return data
    except Exception as e:
        print(f"Error generating learning path: {e}")

    # Fallback generic structured path
    return {
        "title": f"Structured Learning Path: {topic_clean}",
        "description": f"A progressive curriculum taking you through {topic_clean} from fundamentals to applied mastery.",
        "modules": [
            {"order": 1, "title": f"Fundamentals of {topic_clean}", "description": "Core principles, terminology, and foundational concepts.", "duration": "1.5 hrs"},
            {"order": 2, "title": f"Core Mechanics & Principles", "description": "Working mechanisms and key functional components.", "duration": "2.0 hrs"},
            {"order": 3, "title": f"Practical Applications & Problem Solving", "description": "Hands-on examples, case studies, and common patterns.", "duration": "2.5 hrs"},
            {"order": 4, "title": f"Intermediate Relationships & Workflows", "description": "How sub-concepts interact and real-world system architecture.", "duration": "2.0 hrs"},
            {"order": 5, "title": f"Advanced Topics & Mastery", "description": "Edge cases, performance considerations, and expert synthesis.", "duration": "3.0 hrs"}
        ]
    }


def generate_learning_path_mermaid(path_data):
    """Generate a Mermaid graph LR definition from the learning path."""
    modules = path_data.get("modules", [])
    if not modules:
        return ""

    lines = ["graph LR"]
    for i, mod in enumerate(modules):
        node_id = f"m{mod.get('order', i + 1)}"
        title = mod.get("title", f"Module {i + 1}").replace('"', "'")
        lines.append(f'    {node_id}["{mod.get("order", i+1)}. {title}"]')
        if i > 0:
            prev_id = f"m{modules[i - 1].get('order', i)}"
            lines.append(f"    {prev_id} --> {node_id}")

    return "\n".join(lines)
