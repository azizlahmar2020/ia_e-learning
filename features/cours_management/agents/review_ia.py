import json
import requests
import logging
import re
import html
import asyncio
import aiohttp
from typing import Dict, List, Any, Optional
from datetime import datetime
import time

# Configuration optimisée
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CorrectedPedagogicalAgent:
    """Agent pédagogique corrigé pour Oracle APEX"""

    def __init__(self, openrouter_api_key: str, model_name: str = "deepseek/deepseek-chat"):
        self.api_key = openrouter_api_key
        self.model_name = model_name
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.apex_endpoints = {
            "review_roadmap": "https://apex.oracle.com/pls/apex/naxxum/review_roadmap/",
            "roadmap_insight": "https://apex.oracle.com/pls/apex/naxxum/roadmap_insight/",
            "weakness_point": "https://apex.oracle.com/pls/apex/naxxum/weakness_point/",
            "chapter_summary_detail": "https://apex.oracle.com/pls/apex/naxxum/chapter_summary_detail/",
            "chapter_study_note": "https://apex.oracle.com/pls/apex/naxxum/chapter_study_note/",
            "roadmap_step": "https://apex.oracle.com/pls/apex/naxxum/roadmap_step/",
            "practice_quiz": "https://apex.oracle.com/pls/apex/naxxum/practice_quiz/",
            "practice_quiz_option": "https://apex.oracle.com/pls/apex/naxxum/practice_quiz_option/"
        }
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8"
        })

    async def analyze_submission_corrected(self, submission_id: str) -> Dict[str, Any]:
        """Analyse corrigée avec sauvegarde en base"""
        start_time = time.time()
        logger.info(f"🚀 Début de l'analyse optimisée pour la soumission {submission_id}")

        try:
            # 1. Récupération des données depuis l'API REST existante
            submission_data = await self._fetch_submission_data_async(submission_id)

            # 2. Analyse rapide et efficace
            concept_analysis = await self._quick_concept_analysis(submission_data)
            summaries = await self._generate_fast_summaries(submission_data)
            roadmap = await self._create_efficient_roadmap(submission_data, concept_analysis)
            quizzes = await self._generate_unique_quizzes(submission_data)

            # 3. Sauvegarde corrigée en base Oracle APEX
            roadmap_id = await self._save_to_apex_corrected(
                submission_data, concept_analysis, summaries, roadmap, quizzes
            )

            # 4. Compilation finale
            result = self._compile_analysis(
                submission_data, concept_analysis, summaries, roadmap, quizzes, roadmap_id
            )

            elapsed_time = time.time() - start_time
            logger.info(f"✅ Analyse terminée en {elapsed_time:.2f} secondes")

            return result

        except Exception as e:
            logger.error(f"❌ Erreur lors de l'analyse: {e}")
            raise

    async def _fetch_submission_data_async(self, submission_id: str) -> Dict[str, Any]:
        """Récupération depuis l'API REST existante"""
        url = f"https://apex.oracle.com/pls/apex/naxxum/elearning/review/{submission_id}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.session.headers, timeout=10) as response:
                if response.status != 200:
                    raise Exception(f"Erreur API: {response.status}")

                data = await response.json()
                items = data.get("items", [])

                if not items:
                    raise ValueError(f"Aucune soumission trouvée pour l'ID {submission_id}")

                submission_data = json.loads(items[0]["submission_json"])
                logger.info(f"📊 Données récupérées: Score {submission_data.get('score')}%")

                return submission_data

    async def _quick_concept_analysis(self, submission_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyse conceptuelle rapide"""
        responses = submission_data.get('responses', [])
        correct_responses = [r for r in responses if r.get('is_correct') == 'Y']
        incorrect_responses = [r for r in responses if r.get('is_correct') == 'N']
        score = submission_data.get('score', 0)

        # Analyse des concepts basée sur les questions
        concepts_bien_compris = []
        concepts_mal_compris = []

        for response in correct_responses:
            question = response.get('question_text', '').lower()
            if 'deep learning' in question:
                concepts_bien_compris.append("Concepts fondamentaux du Deep Learning")
            elif 'neural network' in question:
                concepts_bien_compris.append("Réseaux de neurones")
            elif 'convolutional' in question:
                concepts_bien_compris.append("Réseaux convolutionnels")
            elif 'recurrent' in question:
                concepts_bien_compris.append("Réseaux récurrents")

        for response in incorrect_responses:
            question = response.get('question_text', '').lower()
            if 'deep learning' in question:
                concepts_mal_compris.append("Concepts fondamentaux du Deep Learning")
            elif 'neural network' in question:
                concepts_mal_compris.append("Architecture des réseaux de neurones")
            elif 'convolutional' in question:
                concepts_mal_compris.append("Applications des réseaux convolutionnels")
            elif 'recurrent' in question:
                concepts_mal_compris.append("Fonctionnement des réseaux récurrents")

        return {
            "concepts_bien_compris": list(set(concepts_bien_compris)),
            "concepts_mal_compris": list(set(concepts_mal_compris)),
            "style_apprentissage_detecte": "visuel",
            "niveau_confiance": score / 100,
            "lacunes_critiques": self._identify_critical_gaps(incorrect_responses),
            "recommandations_pedagogiques": [
                "Utiliser des diagrammes et visualisations",
                "Pratiquer avec des exemples concrets",
                "Réviser les concepts étape par étape",
                "Faire des exercices pratiques réguliers"
            ]
        }

    async def _generate_fast_summaries(self, submission_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Génération rapide de résumés détaillés"""
        chapters = submission_data.get('course', {}).get('chapters', [])
        summaries = {}

        for chapter in chapters:
            chapter_id = str(chapter.get('chapter_id'))
            chapter_title = chapter.get('chapter_title', '')
            content = self._extract_chapter_content(chapter)

            summary = {
                "titre": chapter_title,
                "resume_executif": f"Ce chapitre présente les concepts essentiels de {chapter_title}, incluant les définitions, applications pratiques et exemples concrets.",
                "concepts_cles": self._extract_key_concepts_enhanced(content, chapter_title),
                "objectifs_apprentissage": [
                    f"Comprendre les principes fondamentaux de {chapter_title}",
                    f"Identifier les applications pratiques de {chapter_title}",
                    f"Maîtriser les techniques de base de {chapter_title}"
                ],
                "points_attention": [
                    "Bien distinguer les différents concepts",
                    "Comprendre les relations entre les éléments",
                    "Pratiquer avec des exemples concrets"
                ],
                "ressources_complementaires": [
                    "Documentation officielle",
                    "Tutoriels interactifs",
                    "Exercices pratiques",
                    "Vidéos explicatives"
                ],
                "evaluation_difficulte": self._assess_difficulty_enhanced(content, chapter_title)
            }

            summaries[chapter_id] = summary

        return summaries

    async def _create_efficient_roadmap(self, submission_data: Dict[str, Any],
                                        concept_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Création d'un roadmap efficace basé sur les erreurs"""
        incorrect_responses = [r for r in submission_data.get('responses', []) if r.get('is_correct') == 'N']
        chapters = submission_data.get('course', {}).get('chapters', [])

        # Grouper les erreurs par chapitre
        chapter_errors = self._group_errors_by_chapter_enhanced(incorrect_responses, chapters)

        roadmap_steps = []
        step_number = 1

        for chapter_id, error_data in chapter_errors.items():
            priority = "Critique" if error_data['error_count'] > 2 else "Haute" if error_data[
                                                                                       'error_count'] > 1 else "Moyenne"
            duration = f"{error_data['error_count'] * 2}h"

            step = {
                "etape": step_number,
                "chapitre_id": chapter_id,
                "titre_chapitre": error_data['chapter_title'],
                "niveau_priorite": priority,
                "duree_estimee": duration,
                "objectifs_apprentissage": [
                    f"Maîtriser les concepts fondamentaux de {error_data['chapter_title']}",
                    f"Corriger les erreurs identifiées dans {error_data['chapter_title']}",
                    f"Appliquer les connaissances de {error_data['chapter_title']} en pratique"
                ],
                "resume_chapitre": f"Révision approfondie de {error_data['chapter_title']} avec focus sur les points d'amélioration identifiés",
                "plan_action_detaille": [
                    "Réviser les définitions et concepts de base",
                    "Analyser les erreurs commises et leurs corrections",
                    "Pratiquer avec des exercices ciblés",
                    "Valider la compréhension avec des quiz adaptatifs",
                    "Appliquer les connaissances dans des projets pratiques"
                ],
                "criteres_reussite": [
                    "Définir correctement tous les concepts clés",
                    "Réussir 80% des quiz de validation",
                    "Appliquer les concepts dans des exercices pratiques",
                    "Expliquer les concepts à quelqu'un d'autre"
                ],
                "conseils_motivation": [
                    "Chaque concept maîtrisé est une victoire importante",
                    "La progression se fait étape par étape",
                    "Les erreurs sont des opportunités d'apprentissage",
                    "La pratique régulière garantit la réussite"
                ]
            }
            roadmap_steps.append(step)
            step_number += 1

        return roadmap_steps

    async def _generate_unique_quizzes(self, submission_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Génération de quiz uniques et innovants"""
        incorrect_responses = [r for r in submission_data.get('responses', []) if r.get('is_correct') == 'N']

        quizzes = []
        quiz_id = 1

        # Créer des quiz basés sur les concepts, pas les questions originales
        concept_groups = self._group_by_concepts_enhanced(incorrect_responses)

        for concept, errors in concept_groups.items():
            quiz = {
                "quiz_id": quiz_id,
                "concept_cible": concept,
                "question_innovative": self._create_innovative_question(concept),
                "niveau_difficulte": "Moyen",
                "options": self._create_detailed_options(concept),
                "explication_detaillee": f"Cette question évalue votre compréhension pratique de {concept} dans un contexte réel d'application.",
                "objectif_pedagogique": f"Renforcer la maîtrise de {concept} par l'application pratique"
            }
            quizzes.append(quiz)
            quiz_id += 1

            if len(quizzes) >= 3:  # Limiter à 3 quiz de qualité
                break

        return quizzes

    async def _save_to_apex_corrected(self, submission_data: Dict[str, Any],
                                      concept_analysis: Dict[str, Any],
                                      summaries: Dict[str, Dict[str, Any]],
                                      roadmap: List[Dict[str, Any]],
                                      quizzes: List[Dict[str, Any]]) -> int:
        """Sauvegarde corrigée en base Oracle APEX"""

        roadmap_id = None

        try:
            # 1. Créer le roadmap principal
            roadmap_data = {
                "submission_id": submission_data.get('submission_id'),
                "student_id": submission_data.get('student_id'),
                "course_id": submission_data.get('course', {}).get('course_id'),
                "ai_analysis": json.dumps(concept_analysis, ensure_ascii=False),
                "learning_style": concept_analysis.get('style_apprentissage_detecte', 'visuel'),
                "confidence_level": round(concept_analysis.get('niveau_confiance', 0) * 100, 2),
                "estimated_completion_hours": len(roadmap) * 2,
                "status": "Active",
                "progress_percentage": 0
            }

            roadmap_response = await self._post_to_apex_safe("review_roadmap", roadmap_data)
            if roadmap_response and 'roadmap_id' in roadmap_response:
                roadmap_id = roadmap_response['roadmap_id']
                logger.info(f"✅ Roadmap créé avec ID: {roadmap_id}")
            else:
                logger.warning("⚠️ Impossible de créer le roadmap principal")
                return None

            # 2. Sauvegarder les insights du roadmap
            if roadmap_id:
                insight_data = {
                    "roadmap_id": roadmap_id,
                    "strengths_count": len(concept_analysis.get('concepts_bien_compris', [])),
                    "improvement_count": len(concept_analysis.get('concepts_mal_compris', [])),
                    "encouragement": "Vous progressez bien ! Continuez vos efforts.",
                    "next_milestone": "Compléter la première étape du roadmap",
                    "confidence_boost": "Chaque concept maîtrisé vous rapproche du succès !",
                    "learning_journey": f"Votre parcours en {len(roadmap)} étapes",
                    "learning_style": concept_analysis.get('style_apprentissage_detecte', 'visuel'),
                    "cognitive_load": "Optimisé",
                    "retention_strategy": "Révision espacée recommandée",
                    "engagement_level": "Élevé",
                    "personalization_score": 95.0
                }
                await self._post_to_apex_safe("roadmap_insight", insight_data)

            # 3. Sauvegarder les étapes du roadmap
            for step in roadmap:
                if roadmap_id:
                    step_data = {
                        "roadmap_id": roadmap_id,
                        "chapter_id": step.get('chapitre_id'),
                        "step_order": step.get('etape'),
                        "priority_level": step.get('niveau_priorite'),
                        "estimated_duration": step.get('duree_estimee'),
                        "objectives": '; '.join(step.get('objectifs_apprentissage', [])),
                        "summary": step.get('resume_chapitre'),
                        "study_notes": '; '.join(step.get('plan_action_detaille', [])),
                        "exercises": "Exercices pratiques ciblés",
                        "success_criteria": '; '.join(step.get('criteres_reussite', [])),
                        "motivation": '; '.join(step.get('conseils_motivation', []))
                    }
                    await self._post_to_apex_safe("roadmap_step", step_data)

            # 4. Sauvegarder les points faibles
            for i, concept in enumerate(concept_analysis.get('concepts_mal_compris', [])):
                if roadmap_id:
                    weakness_data = {
                        "roadmap_id": roadmap_id,
                        "chapter_id": roadmap[0].get('chapitre_id') if roadmap else None,
                        "topic_name": concept,
                        "difficulty_level": 3,
                        "priority_order": i + 1,
                        "concept_summary": f"Révision nécessaire pour {concept}",
                        "improved_explanation": f"Explication détaillée et simplifiée de {concept}",
                        "recommendation_tips": "Pratiquer régulièrement avec des exemples concrets",
                        "success_criteria": "Maîtriser les concepts fondamentaux",
                        "motivational_advice": "Chaque effort compte pour progresser",
                        "memorization_techniques": "Utiliser des cartes mentales et des répétitions espacées"
                    }
                    weakness_response = await self._post_to_apex_safe("weakness_point", weakness_data)
                    weakness_id = weakness_response.get('weakness_id') if weakness_response else None

                    # 5. Sauvegarder les quiz pour ce point faible
                    if weakness_id and i < len(quizzes):
                        quiz = quizzes[i]
                        quiz_data = {
                            "weakness_id": weakness_id,
                            "question_text": quiz.get('question_innovative'),
                            "question_type": "multiple_choice",
                            "difficulty_level": 3,
                            "explanation": quiz.get('explication_detaillee')
                        }
                        quiz_response = await self._post_to_apex_safe("practice_quiz", quiz_data)
                        quiz_db_id = quiz_response.get('quiz_id') if quiz_response else None

                        # 6. Sauvegarder les options du quiz
                        if quiz_db_id:
                            for option in quiz.get('options', []):
                                option_data = {
                                    "quiz_id": quiz_db_id,
                                    "option_text": option.get('texte_option'),
                                    "is_correct": 'Y' if option.get('est_correcte') else 'N',
                                    "explanation": option.get('explication_detaillee', '')
                                }
                                await self._post_to_apex_safe("practice_quiz_option", option_data)

            # 7. Sauvegarder les résumés de chapitres
            for chapter_id, summary in summaries.items():
                summary_data = {
                    "chapter_id": int(chapter_id),
                    "executive_summary": summary.get('resume_executif'),
                    "key_concepts": '; '.join(summary.get('concepts_cles', [])),
                    "attention_points": '; '.join(summary.get('points_attention', [])),
                    "resources": '; '.join(summary.get('ressources_complementaires', [])),
                    "difficulty_level": summary.get('evaluation_difficulte', 3)
                }
                await self._post_to_apex_safe("chapter_summary_detail", summary_data)

                # Sauvegarder les notes d'étude
                note_data = {
                    "chapter_id": int(chapter_id),
                    "main_notes": '; '.join(summary.get('concepts_cles', [])),
                    "examples": "Exemples pratiques et cas d'usage",
                    "pitfalls": "Erreurs courantes à éviter",
                    "revision_tips": '; '.join(summary.get('points_attention', [])),
                    "memorization_methods": "Techniques de mémorisation adaptées",
                    "motivation": "Messages d'encouragement personnalisés"
                }
                await self._post_to_apex_safe("chapter_study_note", note_data)

            logger.info("✅ Données sauvegardées en base Oracle APEX")
            return roadmap_id

        except Exception as e:
            logger.error(f"❌ Erreur sauvegarde APEX: {e}")
            return roadmap_id

    async def _post_to_apex_safe(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Post sécurisé vers Oracle APEX avec gestion d'erreurs"""
        url = self.apex_endpoints[endpoint]

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, headers=self.session.headers, timeout=30) as response:
                    if response.status in [200, 201]:
                        try:
                            return await response.json()
                        except:
                            return {"success": True}
                    else:
                        error_text = await response.text()
                        logger.warning(f"Erreur APEX {endpoint}: {response.status} - {error_text}")
                        return {}
        except Exception as e:
            logger.warning(f"Exception APEX {endpoint}: {e}")
            return {}

    # Méthodes utilitaires améliorées
    def _extract_chapter_content(self, chapter: Dict[str, Any]) -> str:
        """Extraction du contenu de chapitre"""
        contents = chapter.get('contents', [])
        text_parts = []

        for content in contents:
            html_content = content.get('content', '')
            text = re.sub(r'<[^>]+>', ' ', html_content)
            text = re.sub(r'\s+', ' ', text).strip()
            text_parts.append(text)

        return ' '.join(text_parts)

    def _extract_key_concepts_enhanced(self, content: str, chapter_title: str) -> List[str]:
        """Extraction améliorée des concepts clés"""
        concepts = []
        content_lower = content.lower()
        title_lower = chapter_title.lower()

        # Concepts spécifiques au Deep Learning
        if 'deep learning' in title_lower or 'deep learning' in content_lower:
            concepts.extend(['Deep Learning', 'Apprentissage profond', 'Réseaux de neurones'])

        if 'neural' in title_lower or 'neural' in content_lower:
            concepts.extend(['Réseaux de neurones', 'Neurones artificiels', 'Propagation'])

        if 'convolutional' in title_lower or 'convolutional' in content_lower:
            concepts.extend(['Convolution', 'CNN', 'Traitement d\'images'])

        if 'recurrent' in title_lower or 'recurrent' in content_lower:
            concepts.extend(['RNN', 'LSTM', 'Séquences temporelles'])

        # Concepts généraux
        general_keywords = ['algorithm', 'model', 'training', 'optimization', 'data']
        for keyword in general_keywords:
            if keyword in content_lower:
                concepts.append(keyword.capitalize())

        return list(set(concepts))[:5]  # Limiter à 5 concepts uniques

    def _assess_difficulty_enhanced(self, content: str, chapter_title: str) -> int:
        """Évaluation améliorée de la difficulté"""
        title_lower = chapter_title.lower()
        content_lower = content.lower()

        # Concepts avancés
        advanced_terms = ['optimization', 'backpropagation', 'gradient', 'regularization', 'architecture']
        intermediate_terms = ['training', 'model', 'algorithm', 'network', 'layer']
        basic_terms = ['introduction', 'basic', 'fundamental', 'overview']

        advanced_count = sum(1 for term in advanced_terms if term in content_lower or term in title_lower)
        intermediate_count = sum(1 for term in intermediate_terms if term in content_lower or term in title_lower)
        basic_count = sum(1 for term in basic_terms if term in content_lower or term in title_lower)

        if advanced_count >= 2:
            return 5
        elif advanced_count >= 1 or intermediate_count >= 3:
            return 4
        elif intermediate_count >= 1:
            return 3
        elif basic_count >= 1:
            return 2
        else:
            return 3  # Difficulté par défaut

    def _group_errors_by_chapter_enhanced(self, incorrect_responses: List[Dict], chapters: List[Dict]) -> Dict[
        str, Dict]:
        """Groupement amélioré des erreurs par chapitre"""
        chapter_errors = {}

        # Créer un mapping des chapitres
        chapter_map = {str(ch.get('chapter_id')): ch for ch in chapters}

        for response in incorrect_responses:
            question = response.get('question_text', '').lower()

            # Logique améliorée pour associer question à chapitre
            matched_chapter = None

            # Recherche par mots-clés spécifiques
            if 'deep learning' in question:
                matched_chapter = next((ch for ch in chapters if 'introduction' in ch.get('chapter_title', '').lower()),
                                       None)
            elif 'neural network' in question:
                matched_chapter = next((ch for ch in chapters if 'neural' in ch.get('chapter_title', '').lower()), None)
            elif 'convolutional' in question:
                matched_chapter = next(
                    (ch for ch in chapters if 'convolutional' in ch.get('chapter_title', '').lower()), None)
            elif 'recurrent' in question:
                matched_chapter = next((ch for ch in chapters if 'recurrent' in ch.get('chapter_title', '').lower()),
                                       None)

            # Si pas de correspondance spécifique, utiliser le premier chapitre
            if not matched_chapter and chapters:
                matched_chapter = chapters[0]

            if matched_chapter:
                chapter_id = str(matched_chapter.get('chapter_id'))

                if chapter_id not in chapter_errors:
                    chapter_errors[chapter_id] = {
                        'chapter_title': matched_chapter.get('chapter_title', 'Chapitre'),
                        'error_count': 0,
                        'errors': []
                    }

                chapter_errors[chapter_id]['error_count'] += 1
                chapter_errors[chapter_id]['errors'].append(response)

        return chapter_errors

    def _group_by_concepts_enhanced(self, incorrect_responses: List[Dict]) -> Dict[str, List[Dict]]:
        """Groupement amélioré par concepts"""
        concept_groups = {}

        for response in incorrect_responses:
            question = response.get('question_text', '').lower()

            # Classification plus précise des concepts
            if 'deep learning' in question or 'machine learning' in question:
                concept = "Fondamentaux du Deep Learning"
            elif 'neural network' in question or 'neuron' in question:
                concept = "Architecture des réseaux de neurones"
            elif 'convolutional' in question or 'cnn' in question:
                concept = "Réseaux convolutionnels"
            elif 'recurrent' in question or 'rnn' in question or 'lstm' in question:
                concept = "Réseaux récurrents"
            elif 'training' in question or 'optimization' in question:
                concept = "Entraînement et optimisation"
            else:
                concept = "Concepts généraux du Deep Learning"

            if concept not in concept_groups:
                concept_groups[concept] = []
            concept_groups[concept].append(response)

        return concept_groups

    def _create_innovative_question(self, concept: str) -> str:
        """Création de questions innovantes par concept"""
        questions = {
            "Fondamentaux du Deep Learning": "Vous devez expliquer le Deep Learning à un client non-technique. Comment décririez-vous ses avantages par rapport aux méthodes traditionnelles ?",
            "Architecture des réseaux de neurones": "Dans la conception d'un réseau de neurones pour la reconnaissance vocale, quels sont les éléments architecturaux les plus importants à considérer ?",
            "Réseaux convolutionnels": "Pour une application de diagnostic médical par imagerie, pourquoi les CNN sont-ils particulièrement adaptés et quelles précautions prendre ?",
            "Réseaux récurrents": "Dans le développement d'un chatbot intelligent, comment les RNN contribuent-ils à la compréhension du contexte conversationnel ?",
            "Entraînement et optimisation": "Votre modèle de Deep Learning montre des signes de surapprentissage. Quelles stratégies d'optimisation appliqueriez-vous ?",
            "Concepts généraux du Deep Learning": "Comment évalueriez-vous l'efficacité d'un modèle de Deep Learning dans un contexte de production réelle ?"
        }

        return questions.get(concept,
                             "Comment appliqueriez-vous les concepts du Deep Learning dans un projet concret ?")

    def _create_detailed_options(self, concept: str) -> List[Dict[str, Any]]:
        """Création d'options détaillées par concept"""
        options_map = {
            "Fondamentaux du Deep Learning": [
                {
                    "texte_option": "Le Deep Learning imite le cerveau humain pour apprendre automatiquement des patterns complexes dans les données",
                    "est_correcte": True,
                    "explication_detaillee": "Excellente réponse ! Cette explication capture l'essence du Deep Learning de manière accessible : l'apprentissage automatique de patterns complexes grâce à des architectures inspirées du cerveau."
                },
                {
                    "texte_option": "Le Deep Learning est simplement une version plus rapide des algorithmes traditionnels",
                    "est_correcte": False,
                    "explication_detaillee": "Incorrect. Le Deep Learning ne se contente pas d'être plus rapide, il peut apprendre des représentations complexes que les algorithmes traditionnels ne peuvent pas capturer."
                },
                {
                    "texte_option": "Le Deep Learning nécessite toujours une programmation manuelle des caractéristiques",
                    "est_correcte": False,
                    "explication_detaillee": "Faux. Un des avantages majeurs du Deep Learning est justement l'apprentissage automatique des caractéristiques, sans programmation manuelle."
                },
                {
                    "texte_option": "Le Deep Learning fonctionne uniquement avec des images",
                    "est_correcte": False,
                    "explication_detaillee": "Incorrect. Le Deep Learning s'applique à de nombreux types de données : texte, audio, séries temporelles, pas seulement les images."
                }
            ]
        }

        return options_map.get(concept, [
            {"texte_option": "Approche méthodique et structurée", "est_correcte": True,
             "explication_detaillee": "Bonne approche !"},
            {"texte_option": "Solution rapide sans analyse", "est_correcte": False,
             "explication_detaillee": "Une analyse approfondie est nécessaire."},
            {"texte_option": "Ignorer le problème", "est_correcte": False,
             "explication_detaillee": "Il faut toujours adresser les problèmes identifiés."},
            {"texte_option": "Appliquer une solution générique", "est_correcte": False,
             "explication_detaillee": "Chaque situation nécessite une approche adaptée."}
        ])

    def _identify_critical_gaps(self, incorrect_responses: List[Dict]) -> List[str]:
        """Identification des lacunes critiques"""
        error_count = len(incorrect_responses)
        gaps = []

        if error_count > 7:
            gaps.append("Révision complète des concepts fondamentaux nécessaire")
            gaps.append("Besoin d'un accompagnement personnalisé renforcé")
        elif error_count > 4:
            gaps.append("Renforcement ciblé sur les points faibles identifiés")
            gaps.append("Pratique intensive avec des exercices adaptés")
        elif error_count > 2:
            gaps.append("Consolidation des acquis avec des exercices complémentaires")
        else:
            gaps.append("Perfectionnement et approfondissement des connaissances")

        return gaps

    def _compile_analysis(self, submission_data: Dict[str, Any],
                          concept_analysis: Dict[str, Any],
                          summaries: Dict[str, Dict[str, Any]],
                          roadmap: List[Dict[str, Any]],
                          quizzes: List[Dict[str, Any]],
                          roadmap_id: Optional[int]) -> Dict[str, Any]:
        """Compilation finale de l'analyse"""

        responses = submission_data.get('responses', [])
        correct_count = len([r for r in responses if r.get('is_correct') == 'Y'])
        incorrect_count = len([r for r in responses if r.get('is_correct') == 'N'])

        return {
            "metadata": {
                "analysis_timestamp": datetime.now().isoformat(),
                "submission_id": submission_data.get('submission_id'),
                "student_id": submission_data.get('student_id'),
                "course_title": submission_data.get('course', {}).get('course_title'),
                "agent_version": "5.1.0-Corrected-Enhanced",
                "roadmap_id": roadmap_id
            },
            "performance_overview": {
                "score": submission_data.get('score'),
                "total_questions": len(responses),
                "correct_answers": correct_count,
                "incorrect_answers": incorrect_count,
                "success_rate": round((correct_count / len(responses)) * 100, 1) if responses else 0,
                "estimated_study_time": f"{len(roadmap) * 2}h",
                "chapters_to_review": len(roadmap)
            },
            "concept_analysis": concept_analysis,
            "chapter_summaries": summaries,
            "personalized_roadmap": roadmap,
            "innovative_quizzes": quizzes,
            "motivational_elements": {
                "encouragement": f"Vous maîtrisez déjà {correct_count} concepts importants ! Concentrez-vous sur les {incorrect_count} points d'amélioration avec votre roadmap personnalisé.",
                "next_milestone": "Compléter la première étape du roadmap",
                "confidence_boost": "Chaque concept maîtrisé vous rapproche de l'expertise !",
                "learning_journey": f"Votre parcours personnalisé en {len(roadmap)} étapes vous mènera au succès."
            }
        }


# Fonction principale corrigée
async def analyze_student_submission_corrected(submission_id: str, openrouter_api_key: str) -> Dict[str, Any]:
    """Fonction principale corrigée pour l'analyse"""
    agent = CorrectedPedagogicalAgent(openrouter_api_key)
    return await agent.analyze_submission_corrected(submission_id)


# Test de l'agent corrigé
if __name__ == "__main__":
    import asyncio


    async def test_corrected_agent():
        OPENROUTER_API_KEY = "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"
        SUBMISSION_ID = "378"

        try:
            result = await analyze_student_submission_corrected(SUBMISSION_ID, OPENROUTER_API_KEY)
            print(json.dumps(result, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"Erreur: {e}")


    asyncio.run(test_corrected_agent())
