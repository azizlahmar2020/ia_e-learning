BASE_URL = "https://apex.oracle.com/pls/apex/naxxum/"

# 🔹 Définition des entités et leurs champs (obligatoires et optionnels)
ENTITY_FIELDS = {
    "Course": {
        "optional": ["prerequisites", "content", "target_audience", "description", "tags", "price", "rating"],
        "auto_increment": ["course_id"],
        "default_values": {"instructor_id": 1}
    },
    "User": {
        "optional": ["phone"],
        "required": ["email", "first_name", "last_name", "user_password"],
        "auto_increment": ["user_id"],
        "default_values": {"user_role": "Student"}
    }
}

# 🔹 Définition des relations entre les entités
ENTITY_RELATIONSHIPS = {
    "Course": {"instructor_id": "Foreign Key to Instructor"},
    "Chapter": {"course_id": "Foreign Key to Course"},
    "ChapterContent": {"chapter_id": "Foreign Key to Chapter"}
}

# 🔹 Définition des endpoints API et des méthodes associées
API_ENDPOINTS = {
    "Courses": {
        "GET": "course/",
        "GET_BY_ID": "course/{course_id}",
        "POST": "elearning/course",
        "PUT": "course/{course_id}",
        "DELETE": "course/{course_id}"
    },
    "Chapters": {
        "GET": "chapter/",
        "GET_BY_ID": "chapter/{chapter_id}",
        "PUT": "chapter/{chapter_id}",
        "DELETE": "chapter/{chapter_id}"
    },
    "ChapterContent": {
        "GET": "chapter_content/",
        "GET_BY_ID": "chapter_content/{content_id}",
        "PUT": "chapter_content/{content_id}",
        "DELETE": "chapter_content/{content_id}"
    },
    "Users": {
        "GET": "user/",
        "GET_BY_ID": "user/{user_id}",
        "POST": "users/",
        "PUT": "user/{user_id}",
        "DELETE": "user/{user_id}"
    }
}

# 🔹 Définition des valeurs possibles pour certains champs
STATUS_VALUES = ["Draft", "Published", "Archived"]
# 🔹 Exemple de chapitre structuré (utilisé dans le prompt)
CHAPTER_EXAMPLE = {
    "Title": "Maîtriser les fondamentaux du CSS pour créer des interfaces web modernes, responsives et accessibles",
    "Content": """<h3>Introduction au CSS et son rôle dans le web moderne</h3>
<p>Le <strong>CSS</strong> permet de styliser les pages HTML pour créer des expériences utilisateurs attractives...</p>
<h3>Flexbox et mise en page fluide</h3>
<p>Grâce à <strong>Flexbox</strong>, il est possible d’aligner et de répartir des éléments facilement...</p>
<ul>
  <li><strong>Exemple :</strong> Centrer un bouton dans une div</li>
  <li><strong>Exemple :</strong> Mise en page à colonnes</li>
  <li><strong>Exemple :</strong> Aligner des images horizontalement</li>
  <li><strong>Exemple :</strong> Réorganisation sur petit écran</li>
</ul>
<h3>Les variables CSS pour la cohérence visuelle</h3>
<p>Les <strong>variables CSS</strong> simplifient la gestion des couleurs, tailles, polices...</p>
<h3>Sélecteurs avancés pour un ciblage précis</h3>
<p>Utiliser <strong>:nth-child</strong>, <strong>[data-]</strong>, et les sélecteurs combinés...</p>
<h3>Transitions et animations CSS</h3>
<p>Les animations ajoutent du dynamisme avec <strong>transition</strong> et <strong>@keyframes</strong>...</p>
<h3>Accessibilité et contrastes</h3>
<p>Le CSS doit respecter les normes d’accessibilité : <strong>contrastes</strong>, <strong>focus visibles</strong>...</p>
<h3>Bonnes pratiques et optimisation</h3>
<p>Évitez les sélecteurs lourds, privilégiez les classes dédiées, regroupez les règles...</p>
<div style='background:#E0F7FA; padding:10px'><strong>Note :</strong> Toujours vérifier le contraste texte/fond</div>
<div style='background:#FFF3E0; padding:10px'><strong>Note :</strong> Regrouper les règles pour réduire la redondance</div>
<div style='background:#F3E5F5; padding:10px'><strong>Note :</strong> Préférez les classes utilitaires pour plus de clarté</div>"""
}
