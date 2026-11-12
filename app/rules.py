"""Plain rules shared by the API: team gaps, rejection checks and the rule-based fallbacks.

These mirror the rules in the web page so the AI drafts and the screens agree.
"""
import re

STRONG = 70
PARTIAL = 40


def level(v):
    return "strong" if v >= STRONG else "partial" if v >= PARTIAL else "none"


def skills(state):
    return state["role"]["skills"]


def core(state):
    return [k for k in skills(state) if k["core"]]


def skill(state, sid):
    return next((k for k in skills(state) if k["id"] == sid), None)


def low(name):
    if re.match(r"^(Arabic|English|French)", name):
        return name
    return name[:1].lower() + name[1:]


def first(name):
    return (name or "").split(" ")[0]


def join_list(xs):
    xs = list(xs)
    if len(xs) < 2:
        return "".join(xs)
    return ", ".join(xs[:-1]) + " and " + xs[-1]


def rating(member, sid):
    mgr = member.get("mgr") or {}
    if sid in mgr and mgr[sid] is not None:
        return mgr[sid]
    return (member.get("self") or {}).get(sid, 1)


def team_count(state, sid):
    return sum(1 for m in state["team"] if rating(m, sid) == 3)


def need(state, k):
    return state["role"]["coreTarget"] if k["core"] else state["role"]["niceTarget"]


def is_gap(state, k):
    return team_count(state, k["id"]) < need(state, k)


def fills(state, cand):
    return [k for k in skills(state) if is_gap(state, k) and cand["ev"].get(k["id"], 0) >= STRONG]


def mentors_for(state, sid):
    return [m for m in state["team"] if (m.get("mentor") or {}).get("willing") and sid in (m.get("mentor") or {}).get("skills", [])]


def not_strong_in(state, sid):
    return [m for m in state["team"] if rating(m, sid) < 3]


def learn_skills(state, cand):
    return [k for k in core(state) if cand["ev"].get(k["id"], 0) < STRONG]


def reason_skill(state, cand):
    return sorted(core(state), key=lambda k: cand["ev"].get(k["id"], 0))[0]


# ---------- rejection messages ----------

def template_rejection(state, cand, kind="level"):
    k = reason_skill(state, cand)
    role = state["role"]["title"]
    if kind == "more":
        return (f"Thank you for applying for the {role} role. We chose a candidate whose CV showed deeper experience in "
                f"{low(k['name'])}, including {k['good']}, which this role needs to be successful.")
    return (f"Thank you for applying for the {role} role. Based on the CV you shared, your experience in {low(k['name'])} "
            f"wasn’t yet at the level this role needs to be successful. We’re looking for a track record of {k['good']}.")


AGE_WORDS = re.compile(r"\b\d+\s*\+?\s*(years?|yrs)\b|years of experience|too (young|old)|junior|senior enough", re.I)


def check_rejection(state, cand, text):
    """Return a list of (ok, label). Mirrors the checks shown on screen."""
    k = reason_skill(state, cand)
    t = (text or "").lower()
    names_skill = k["name"].lower() in t
    others = [x for x in core(state) if x["id"] != k["id"] and x["name"].lower() in t]
    ok_skill = names_skill and not others
    no_years = not AGE_WORDS.search(text or "")
    return [
        (ok_skill, "Names one core skill" if ok_skill else "Should name one core skill only"),
        (no_years, "Level of experience, not years" if no_years else "Mentions years or age-linked words"),
        (True, "Asks the candidate to opt in"),
    ]


def rejection_ok(state, cand, text):
    return all(ok for ok, _ in check_rejection(state, cand, text)) and 20 <= len(text or "") <= 600


# ---------- onboarding plan ----------

def plan_for(state, cand):
    learn = learn_skills(state, cand)
    bring = fills(state, cand)
    exec_lead = (mentors_for(state, "exec") or [None])[0]
    clients = [c["name"] for c in state["clients"]]
    main_client = clients[0] if clients else "the main client"
    d30 = [f"Meet the account teams for {join_list(clients)}, and read each client’s insights."]
    for k in learn[:2]:
        co = (mentors_for(state, k["id"]) or [None])[0]
        d30.append(f"{'Pair with ' + co['name'] if co else 'Find a mentor'} on {low(k['name'])}: shadow two pieces of their work.")
    if exec_lead:
        d30.append(f"Join two client meetings led by {exec_lead['name']}.")
    d60 = [f"Lead a discovery session with {main_client}, with a mentor observing and giving feedback."]
    for k in bring[:2]:
        me = [first(m["name"]) for m in not_strong_in(state, k["id"])][:2]
        d60.append(f"Start fortnightly sessions teaching {low(k['name'])}" + (f" to {join_list(me)}" if me else "") + ".")
    for k in learn[:1]:
        d60.append(f"Deliver one piece of {low(k['name'])} work with a mentor reviewing it.")
    d90 = [f"Own one {main_client} workstream end to end."]
    for k in bring[:1]:
        d90.append(f"Run a team session on {low(k['name'])}.")
    d90.append("Review progress" + (f" on {join_list(low(k['name']) for k in learn)}" if learn else "") +
               " with the manager and agree the next steps.")
    return {"d30": d30, "d60": d60, "d90": d90}
