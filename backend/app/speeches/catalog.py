"""Curated speech catalog."""
from __future__ import annotations

SPEECH_CATALOG: list[dict] = [
    {
        "id": "kennedy-inaugural-1961-01-20",
        "figure": "John F. Kennedy",
        "title": "Inaugural Address",
        "year": 1961,
        "era": "Cold War",
        "description": "Kennedy's 1961 inaugural address called on Americans to ask what they could do for their country, setting the tone for a new generation of leadership during the Cold War.",
        "has_recording": True,
    },
    {
        "id": "gettysburg-1863",
        "figure": "Abraham Lincoln",
        "title": "Gettysburg Address",
        "year": 1863,
        "era": "Civil War",
        "description": "Delivered during the dedication of the Soldiers' National Cemetery, Lincoln redefined the purpose of the Civil War and American democracy.",
        "has_recording": False,
    },
    {
        "id": "ihaveadream-1963",
        "figure": "Martin Luther King Jr.",
        "title": "I Have a Dream",
        "year": 1963,
        "era": "Civil Rights Movement",
        "description": "Delivered at the March on Washington, King's iconic speech articulated the vision of racial equality and justice for all Americans.",
        "has_recording": True,
    },
    {
        "id": "fdr-infamy-1941",
        "figure": "Franklin D. Roosevelt",
        "title": "Day of Infamy Speech",
        "year": 1941,
        "era": "World War II",
        "description": "FDR's address to Congress following the attack on Pearl Harbor requested a declaration of war against Japan.",
        "has_recording": True,
    },
    {
        "id": "sojourner-truth-aint-i-a-woman-1851",
        "figure": "Sojourner Truth",
        "title": "Ain't I a Woman?",
        "year": 1851,
        "era": "Antebellum America",
        "description": "Truth's extemporaneous speech at the Women's Rights Convention challenged both racial and gender inequality with piercing logic and personal testimony.",
        "has_recording": False,
    },
    {
        "id": "lincoln-second-inaugural-1865",
        "figure": "Abraham Lincoln",
        "title": "Second Inaugural Address",
        "year": 1865,
        "era": "Civil War",
        "description": "With 'malice toward none,' Lincoln outlined his vision for Reconstruction and national healing as the Civil War neared its end.",
        "has_recording": False,
    },
]


def get_speech_by_id(speech_id: str) -> dict | None:
    """Return the speech dict matching speech_id, or None."""
    for speech in SPEECH_CATALOG:
        if speech["id"] == speech_id:
            return speech
    return None
