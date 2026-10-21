"""Dictionary-based detection of Catalog Skills in free (English) Offer text.

One compiled regex per Skill. It includes the Skill name, every alias of
``catalog/aliases.csv`` that points to it (except the unsafe ones listed
below) and the extra text synonyms in ``TEXT_SYNONYMS``. Matching is
case-insensitive unless a rule says otherwise (inline ``(?-i:...)``).

Word boundaries use lookarounds instead of ``\\b`` so symbols work
(``c++``, ``c#``, ``node.js``, ``ci/cd``): a term must not be preceded by
``[\\w.+#]`` nor followed by ``[\\w+#]``. This is also why "javascript" is not
"java", and "MySQL", "PostgreSQL" and "NoSQL" are not "sql".
"""

import re

from skillpath.frequency import normalize_skill

_LEFT = r"(?<![\w.+#])"
_RIGHT = r"(?![\w+#])"

# Aliases of aliases.csv that must NOT be used as free-text terms.
# "rest" is an ordinary English word (rule for `rest api` below).
UNSAFE_ALIASES = {"rest", "restful"}
# Short acronyms that only count in their exact upper-case form.
CASE_SENSITIVE_ALIASES = {"js": "JS", "ml": "ML", "nlp": "NLP", "oop": "OOP"}

# Languages/tools that, in a list next to "R" or "Go", make it unambiguous.
_LANGS = (
    r"python|java|javascript|typescript|c\+\+|c#|ruby|rust|scala|kotlin|php|perl|swift|"
    r"node\.js|sql|sas|stata|spss|matlab|julia|excel|tableau|power\s?bi|spark|hadoop|vba|"
    r"bash|golang"
)
_LIST_SEP = r"\s*(?:,|/|&|\bor\b|\band\b|\|)\s*(?:and\s+|or\s+)?"

# --- Ambiguous Skills: custom rules (replace the automatic name term) --------
CUSTOM_TERMS: dict[str, list[str]] = {
    # `r`: only the capital letter R, and only in unambiguous contexts:
    #  - "RStudio" / "R Studio" / "R Shiny" / "R Markdown", "R programming|language|packages";
    #  - "in/with/using/of R" (e.g. "experience in R or Python"), R not followed by "&" ("R&D")
    #    or an apostrophe/word character;
    #  - R in a list next to another language/tool ("Python, R", "R or SAS", "R/Python").
    # Never: "R&D", "(r)" lowercase, initials like "Mr. R", a lone letter.
    "r": [
        r"rstudio",
        r"(?-i:R)\s+(?:studio|shiny|markdown|programming|language|packages?|scripts?|libraries|code)\b",
        r"\b(?:in|with|using|use|of|knowledge\s+of|and|or)\s+(?-i:R)(?![\w+#&'’.-]|\.\w)(?=\W|$)",
        rf"(?:{_LANGS}){_LIST_SEP}(?-i:R)(?![\w+#&'’-]|\.\w)",
        rf"(?<![\w.+#&])(?-i:R){_LIST_SEP}(?:{_LANGS})",
    ],
    # `go`: "Golang", "Go programming/language", or capital Go next to another
    # language in a list ("Python, Go, Java"). Never the verb "go" (lowercase or
    # capital "Go to market", "Go beyond").
    "go": [
        r"golang",
        r"(?-i:Go)\s+(?:programming|language|lang)\b",
        rf"(?:{_LANGS}){_LIST_SEP}(?-i:Go)(?![\w+#])",
        rf"(?<![\w.+#])(?-i:Go){_LIST_SEP}(?:{_LANGS})",
    ],
    # `excel`: the tool, never the verb. Accepted: "Microsoft/MS Excel" (also
    # via aliases), capital "Excel" not followed by a typical verb complement
    # ("Excel in", "Excel at") and not preceded by "to/will/can/must", or
    # lowercase "excel" followed by a spreadsheet noun ("excel spreadsheets").
    "excel": [
        r"(?:microsoft|ms|office)\s+excel",
        r"excel\s+(?:spreadsheets?|sheets?|workbooks?|formulas?|macros?|models?|pivot|dashboards?|files?|reports?|skills|proficiency)",
        r"(?<!\bto\s)(?<!\bwill\s)(?<!\bcan\s)(?<!\bmust\s)(?<!\bto\sreally\s)"
        r"(?-i:EXCEL|Excel)(?!\s+(?:in|at|as|within|beyond|under|while|when|by|from|your|their|our|and\s+(?:grow|thrive|succeed|develop|lead|learn|contribute)))",
    ],
    # `spark`: Apache Spark, PySpark, Spark SQL/Streaming, or capital "Spark"
    # as a tool (in a list or followed by a technical word). Not the word "spark".
    "spark": [
        r"pyspark",
        r"spark\s+(?:sql|streaming|mllib|jobs?|clusters?|dataframes?|applications?)",
        rf"(?:{_LANGS}|hive|kafka|airflow|databricks|flink){_LIST_SEP}(?-i:Spark)(?![\w+#])",
        rf"(?<![\w.+#])(?-i:Spark){_LIST_SEP}(?:{_LANGS}|hive|kafka|airflow|databricks|flink)",
    ],
    # `rest api`: "REST API(s)", "RESTful", "REST services/endpoints/web services".
    # Never the word "rest" alone ("rest of the team").
    "rest api": [
        r"restful",
        r"(?-i:REST)(?:\s+web)?\s*[- ]?\s*(?:apis?|services?|endpoints?|interfaces?|architecture)",
        r"rest(?:ful)?\s+apis?",
    ],
    # `react`: capital React only (the verb "react" is common). React.js/ReactJS in any case.
    "react": [r"(?-i:React)(?:\.?js|\s+native)?", r"react\.?js"],
    # `sql`: not MySQL/PostgreSQL/NoSQL/SQLite (the left boundary excludes them), and
    # not "SQL Server" (a separate Skill: `sql server`). In asaniczka `sql` and
    # `mysql` are different Skills, so "MySQL" does not count as `sql`.
    "sql": [r"sql(?!\s+server)"],
    # `oracle`: the database/ecosystem; not the company name in "Oracle Corporation".
    # Nor Oracle ERP/Fusion/EBS/PeopleSoft/NetSuite/Hyperion applications (not the database).
    "oracle": [
        r"oracle(?!\s+(?:corp|corporation|inc|erp|cloud\s+erp|fusion|ebs|e-business|peoplesoft|"
        r"hcm|financials|netsuite|hyperion|forms|apps)\b)"
    ],
    # `snowflake`: the platform; not the "snowflake schema" modeling term.
    "snowflake": [r"snowflake(?!\s+schema)"],
    # `scala`: capital Scala (language), not the plain word.
    "scala": [r"(?-i:Scala)"],
    # `agile`: methodology word. Also "scrum" and "kanban" imply it in practice, but
    # they are not counted: job_skills treats them as different Skills.
    "agile": [r"agile"],
    # `git`: the tool and its hosts. GitHub/GitLab/Bitbucket imply git in practice.
    "git": [r"git(?:hub|lab)?", r"bitbucket"],
    # `statistics`: only the noun "statistics". "statistical analysis/methods" is a
    # separate Skill in job_skills, so "statistical" does not count.
    "statistics": [r"statistics"],
    # `azure`: not "Azure DevOps" (a different product, listed apart in job_skills).
    "azure": [r"azure(?![\s-]*dev\s?ops)"],
    # `algorithms`: the CS topic; not "machine learning/ML/statistical/predictive algorithms".
    "algorithms": [r"(?<!learning\s)(?<!ml\s)(?<!statistical\s)(?<!predictive\s)algorithms?"],
    # `data visualization`: "data visualization(s)", "data viz".
    "data visualization": [r"data[\s-]?(?:visuali[sz]ations?|viz)"],
    # `c++` / `c#`: explicit symbols; "C sharp"; C++11/14/17/20.
    "c++": [r"c\+\+(?:\d{2})?"],
    "c#": [r"c#", r"c\s+sharp"],
    # `java`: the boundary already rejects "javascript"; "J2EE" is Java.
    "java": [r"java", r"j2ee"],
}

# --- Extra text synonyms (regex fragments), added to the automatic terms -----
TEXT_SYNONYMS: dict[str, list[str]] = {
    "power bi": [r"power[\s-]?bi"],
    "scikit-learn": [r"scikit[\s-]?learn", r"sklearn"],
    # Only "object-oriented programming/languages" (and the acronym OOP, case-sensitive alias).
    "object-oriented programming": [r"object[\s-]?oriented\s+languages?"],
    "a/b testing": [r"a\s*/\s*b[\s-]?test(?:s|ing)?", r"ab[\s-]test(?:s|ing)?", r"split[\s-]test(?:s|ing)?"],
    "postgresql": [r"postgres(?:ql)?", r"postgre\s?sql"],
    "mysql": [r"my[\s-]?sql"],
    "sql server": [r"(?:ms|microsoft|t)[\s-]?sql\s+server", r"mssql", r"sql\s+server", r"t-sql"],
    "node.js": [r"node\.?\s?js", r"nodejs"],
    "ci/cd": [r"ci\s*/\s*cd", r"ci\s*&\s*cd"],  # "continuous integration" is a separate Skill in job_skills: not counted
    "etl": [r"extract,?\s+transform,?\s+(?:and\s+)?load", r"elt"],
    "data modeling": [r"data[\s-]?model(?:l)?ing"],
    "data warehousing": [r"data[\s-]?warehous(?:e|es|ing)"],
    "data cleaning": [r"data[\s-]?(?:cleaning|cleansing|clean-?up)"],
    "microservices": [r"micro[\s-]?services?"],
    "unit testing": [r"unit[\s-]?test(?:s|ing)?"],
    "machine learning": [r"machine[\s-]?learning"],
    "deep learning": [r"deep[\s-]?learning"],
    "natural language processing": [r"natural[\s-]?language[\s-]?processing"],
    "nosql": [r"no[\s-]?sql"],
    "tensorflow": [r"tensor[\s-]?flow"],
    "pytorch": [r"py[\s-]?torch"],
    "big data": [r"big[\s-]?data"],
    "kubernetes": [r"k8s"],
    "data structures": [r"data[\s-]?structures?"],
    "angular": [r"angular(?:\.?js)?"],
    "docker": [r"docker"],
}


def _term_regex(term: str) -> str:
    """Escape a plain name/alias; spaces and hyphens become ``[\\s-]?``-style separators."""
    tokens = [t for t in re.split(r"[\s-]+", term) if t]
    body = r"[\s-]?".join(re.escape(t) for t in tokens)
    if body and body[-1].isalpha() and not body.endswith("s"):
        body += "s?"
    return body


def build_patterns(
    catalog_names: list[str] | set[str] | dict,
    aliases: dict[str, str],
) -> dict[str, re.Pattern]:
    """One compiled regex per Catalog Skill (keyed by the normalized name)."""
    names = sorted({normalize_skill(n, aliases) for n in catalog_names})
    patterns: dict[str, re.Pattern] = {}
    for name in names:
        fragments: list[str] = list(CUSTOM_TERMS.get(name) or [_term_regex(name)])
        for alias, target in sorted(aliases.items()):
            if target != name or alias in UNSAFE_ALIASES or alias == name:
                continue
            if alias in CASE_SENSITIVE_ALIASES:
                fragments.append(f"(?-i:{CASE_SENSITIVE_ALIASES[alias]})")
            else:
                fragments.append(_term_regex(alias))
        fragments.extend(TEXT_SYNONYMS.get(name, []))
        # Longest-first is not needed: alternation is only tested for presence.
        patterns[name] = re.compile(
            _LEFT + "(?:" + "|".join(dict.fromkeys(fragments)) + ")" + _RIGHT, re.IGNORECASE
        )
    return patterns


def detect_skills(text: str, patterns: dict[str, re.Pattern]) -> set[str]:
    """Skills of ``patterns`` mentioned in ``text``."""
    if not text or not isinstance(text, str):
        return set()
    text = text.replace("\xa0", " ")
    return {skill for skill, pat in patterns.items() if pat.search(text)}
