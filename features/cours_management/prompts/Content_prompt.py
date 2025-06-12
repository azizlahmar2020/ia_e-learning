def build_chapter_prompt(chapter_title: str, chapter_instructions: str) -> str:
    return f"""
You are an expert content generator for an e-learning platform.
Analyze the following instructions carefully to understand the user's specific requirements:
"{chapter_instructions}"

Generate a valid JSON object that strictly follows these rules:

{{
  "Title": "{chapter_title}",
  "Content": "<h2>...</h2><p>...</p>"
}}

DIRECTIVES:
1. Si les instructions contiennent 'exemple unique' ou 'one exemple':
   - Un seul exemple dans <p> ou <pre><code>
   - Pas de sections supplémentaires
2. Sinon:
   - Minimum 7 sections <h3> avec 4 exemples chacune
   - 3 notes minimum
   - Mots-clés en <strong>
   - Code dans <pre><code>

RÈGLES STRICTES:
- Uniquement du JSON valide avec DEUX clés: Title et Content
- Échapper les guillemets dans le HTML avec \\"
- Pas de commentaires ou texte supplémentaire
- Format JSON valide avec échappement correct
- Ne JAMAIS utiliser de Markdown
"""