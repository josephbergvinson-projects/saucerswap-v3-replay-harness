__all__ = ['evaluate_golden_cases', 'run_validation_polish']


def __getattr__(name: str):
    if name == 'evaluate_golden_cases':
        from .golden_cases import evaluate_golden_cases

        return evaluate_golden_cases
    if name == 'run_validation_polish':
        from .polish import run_validation_polish

        return run_validation_polish
    raise AttributeError(name)
