from flask import Flask, Blueprint
import pytest

from mindstack_app.core.module_registry import DEFAULT_MODULES, ModuleDefinition, register_default_modules


def test_default_modules_expose_blueprints():
    for module in DEFAULT_MODULES:
        blueprint = module.load_blueprint()
        assert isinstance(blueprint, Blueprint), f"{module.import_path}.{module.attribute} phải là Blueprint"


def test_register_default_modules_registers_everything():
    app = Flask(__name__)
    register_default_modules(app)

    registered_names = set(app.blueprints.keys())
    expected_names = {module.load_blueprint().name for module in DEFAULT_MODULES}
    assert expected_names.issubset(registered_names)


def test_module_definition_validates_blueprint_type():
    module = ModuleDefinition("mindstack_app.models", "User")

    with pytest.raises(TypeError):
        module.load_blueprint()
