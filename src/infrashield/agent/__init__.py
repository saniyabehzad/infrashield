"""GenAI agent layer (milestone M3).

Planned modules:
    tools.py  - find_sites_at_risk, explain_site, site_report (wrap risk.py results)
    app.py    - Strands agent; model provider switchable between Ollama (local) and Bedrock

Rule: the agent explains computed risk; it never computes or guesses risk itself.
"""
