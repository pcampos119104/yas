from pydantic import BaseModel, Field


class ExerciseStep(BaseModel):
    """One chronological event in a ballet exercise."""

    order: int = Field(ge=1, description="Ordem do passo no exercício")
    action: str = Field(description="Resumo fiel da ação narrada")
    counts: str | None = Field(
        default=None,
        description="Contagem musical exatamente como informada",
    )
    repetitions: int | None = Field(
        default=None,
        ge=1,
        description="Quantidade de repetições, somente quando informada",
    )
    legs_and_feet: str | None = Field(
        default=None,
        description="Ação das pernas e dos pés",
    )
    arms: str | None = Field(default=None, description="Ação dos braços")
    head_and_torso: str | None = Field(
        default=None,
        description="Ação da cabeça e do tronco",
    )
    direction: str | None = Field(
        default=None,
        description="Direção ou orientação espacial informada",
    )
    notes: list[str] = Field(
        default_factory=list,
        description="Outros detalhes explicitamente narrados",
    )


class BalletExercise(BaseModel):
    """A single exercise identified in the narration."""

    title: str = Field(
        min_length=1,
        description=(
            "Título informado ou descrição curta inferida fielmente da narração"
        ),
    )
    starting_position: str | None = Field(
        default=None,
        description="Posição inicial explicitamente informada",
    )
    teacher_tips: list[str] = Field(
        default_factory=list,
        description="Dicas, correções e pontos de atenção dados pela professora",
    )
    steps: list[ExerciseStep] = Field(
        default_factory=list,
        description="Passos em ordem cronológica",
    )


class BalletLesson(BaseModel):
    """Structured exercises extracted from one audio transcript."""

    exercises: list[BalletExercise] = Field(
        default_factory=list,
        description="Exercícios identificados na narração",
    )
    ambiguities: list[str] = Field(
        default_factory=list,
        description="Trechos incertos ou com mais de uma interpretação possível",
    )
