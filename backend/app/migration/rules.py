"""
rules.py — Référentiel des règles de modernisation Java
Ce fichier est utilisé UNIQUEMENT comme documentation de référence.
Les règles ne sont PAS injectées dans le prompt (pour garder le LLM libre),
mais peuvent être utilisées pour enrichir le prompt si besoin.
"""

# ────────────────────────────────────────────────────────────────────────────
# RÈGLES DE MIGRATION PAR VERSION
# ────────────────────────────────────────────────────────────────────────────

JAVA_MIGRATION_RULES = {

    "java_8": {
        "description": "Modernisation vers Java 8",
        "rules": [
            {
                "id": "J8-01",
                "name": "Anonymous classes → Lambda expressions",
                "pattern": "new Runnable() { public void run() { ... } }",
                "modern":  "() -> { ... }",
                "explanation": "Les lambdas remplacent les classes anonymes pour les interfaces fonctionnelles."
            },
            {
                "id": "J8-02",
                "name": "for-each loop → Stream API",
                "pattern": "for (Item item : list) { ... }",
                "modern":  "list.stream().forEach(item -> ...)",
                "explanation": "Les Streams permettent des opérations déclaratives sur les collections."
            },
            {
                "id": "J8-03",
                "name": "Null checks → Optional",
                "pattern": "if (obj != null) { obj.method(); }",
                "modern":  "Optional.ofNullable(obj).ifPresent(o -> o.method())",
                "explanation": "Optional force la gestion explicite des valeurs nulles."
            },
            {
                "id": "J8-04",
                "name": "Date/Calendar → java.time",
                "pattern": "new Date(), Calendar.getInstance()",
                "modern":  "LocalDate, LocalDateTime, ZonedDateTime",
                "explanation": "L'API java.time est thread-safe et bien plus expressive."
            },
        ]
    },

    "java_10": {
        "description": "Modernisation vers Java 10",
        "rules": [
            {
                "id": "J10-01",
                "name": "Type explicite → var (inférence locale)",
                "pattern": "ArrayList<String> list = new ArrayList<String>();",
                "modern":  "var list = new ArrayList<String>();",
                "explanation": "var réduit la verbosité pour les types locaux évidents."
            },
        ]
    },

    "java_14_15": {
        "description": "Modernisation vers Java 14-15",
        "rules": [
            {
                "id": "J14-01",
                "name": "String concatenation → Text Blocks",
                "pattern": 'String sql = "SELECT * FROM " + "users " + "WHERE id = " + id;',
                "modern":  'String sql = """\n                SELECT * FROM users\n                WHERE id = %d\n                """.formatted(id);',
                "explanation": "Les text blocks améliorent la lisibilité des chaînes multilignes."
            },
            {
                "id": "J14-02",
                "name": "if/else chains → Switch expressions",
                "pattern": "if (day == 1) { ... } else if (day == 2) { ... }",
                "modern":  "var result = switch(day) { case 1 -> ...; case 2 -> ...; };",
                "explanation": "Switch expressions sont plus concis et évitent les fall-through accidentels."
            },
        ]
    },

    "java_16_17": {
        "description": "Modernisation vers Java 16-17",
        "rules": [
            {
                "id": "J16-01",
                "name": "Data classes → Records",
                "pattern": "class Point { private int x; private int y; /* getters, equals, hashCode, toString */ }",
                "modern":  "record Point(int x, int y) {}",
                "explanation": "Les records génèrent automatiquement getters, equals, hashCode et toString."
            },
            {
                "id": "J16-02",
                "name": "instanceof + cast → Pattern Matching",
                "pattern": "if (obj instanceof String) { String s = (String) obj; s.length(); }",
                "modern":  "if (obj instanceof String s) { s.length(); }",
                "explanation": "Le pattern matching évite le cast redondant."
            },
            {
                "id": "J17-01",
                "name": "Abstract classes → Sealed classes",
                "pattern": "abstract class Shape { }  class Circle extends Shape { }",
                "modern":  "sealed class Shape permits Circle, Rectangle { }",
                "explanation": "Les sealed classes contrôlent explicitement l'héritage."
            },
        ]
    },

    "general_best_practices": {
        "description": "Bonnes pratiques générales",
        "rules": [
            {
                "id": "BP-01",
                "name": "Raw types → Generics",
                "pattern": "List list = new ArrayList();",
                "modern":  "List<String> list = new ArrayList<>();",
                "explanation": "Les generics apportent la type-safety à la compilation."
            },
            {
                "id": "BP-02",
                "name": "StringBuffer → StringBuilder",
                "pattern": "StringBuffer sb = new StringBuffer();",
                "modern":  "StringBuilder sb = new StringBuilder();",
                "explanation": "StringBuilder est plus performant (non synchronisé) pour usage mono-thread."
            },
            {
                "id": "BP-03",
                "name": "Checked exceptions → Unchecked quand pertinent",
                "pattern": "throws Exception dans chaque signature",
                "modern":  "Utiliser des exceptions spécifiques ou RuntimeException",
                "explanation": "Éviter la propagation aveugle de checked exceptions améliore la lisibilité."
            },
            {
                "id": "BP-04",
                "name": "Magic numbers → Constants",
                "pattern": "if (status == 1) { ... }",
                "modern":  "private static final int ACTIVE_STATUS = 1;  if (status == ACTIVE_STATUS)",
                "explanation": "Les constantes nommées rendent le code auto-documenté."
            },
            {
                "id": "BP-05",
                "name": "Utility class → private constructor",
                "pattern": "public class Utils { public static void helper() {} }",
                "modern":  "Ajouter private Utils() {} pour prévenir l'instanciation",
                "explanation": "Une classe utilitaire ne doit pas être instanciable."
            },
        ]
    }
}


# ────────────────────────────────────────────────────────────────────────────
# HELPER : Obtenir toutes les règles sous forme de texte (optionnel)
# ────────────────────────────────────────────────────────────────────────────
def get_rules_summary() -> str:
    """
    Génère un résumé textuel de toutes les règles.
    Peut être injecté dans le prompt pour guider le LLM si nécessaire.
    """
    lines = ["RÈGLES DE MODERNISATION JAVA :", "=" * 40]
    for category, data in JAVA_MIGRATION_RULES.items():
        lines.append(f"\n🔹 {data['description']}")
        for rule in data["rules"]:
            lines.append(f"  [{rule['id']}] {rule['name']}")
            lines.append(f"       Avant  : {rule['pattern']}")
            lines.append(f"       Après  : {rule['modern']}")
    return "\n".join(lines)


# ────────────────────────────────────────────────────────────────────────────
# PATTERNS OBSOLÈTES DÉTECTABLES (référence rapide)
# ────────────────────────────────────────────────────────────────────────────
OBSOLETE_PATTERNS = [
    "java.util.Date",
    "java.util.Calendar",
    "new Runnable()",
    "new Comparator()",
    "StringBuffer",
    "Vector",
    "Hashtable",
    "Enumeration",
    "instanceof.*cast",       # pattern matching manquant
    "throws Exception",       # trop générique
    "e.printStackTrace()",    # mauvaise gestion des exceptions
    "System.out.println",     # utiliser un logger
]
