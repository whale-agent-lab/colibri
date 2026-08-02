import argparse
import importlib.machinery
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock


HERE = Path(__file__).resolve().parent.parent
CLI = HERE / "coli"


def load_cli():
    loader = importlib.machinery.SourceFileLoader("coli_v4_cli_test", str(CLI))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class V4CliTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cli = load_cli()

    def make_model(self, model_type="deepseek_v4"):
        directory = tempfile.TemporaryDirectory()
        root = Path(directory.name)
        (root / "config.json").write_text(
            json.dumps({"model_type": model_type}), encoding="utf-8"
        )
        (root / "tokenizer.json").write_text("{}", encoding="utf-8")
        return directory, root

    def test_model_arch_detects_deepseek_v4(self):
        directory, root = self.make_model()
        try:
            self.assertEqual(self.cli.model_arch(str(root)), "deepseek_v4")
        finally:
            directory.cleanup()

    def test_engine_for_selects_deepseek_v4_binary(self):
        directory, root = self.make_model()
        try:
            expected = "deepseek_v4.exe" if os.name == "nt" else "deepseek_v4"
            self.assertEqual(Path(self.cli.engine_for(str(root))).name, expected)
        finally:
            directory.cleanup()

    def test_v4_engine_environment_forwards_ram_and_context(self):
        args = argparse.Namespace(
            ngen=8,
            temp=0.0,
            ram=64,
            ctx=4096,
            no_dspark=True,
            draft_model="relative-dspark",
        )
        env = self.cli.env_for_engine(args, "deepseek_v4")
        self.assertEqual(env["NGEN"], "8")
        self.assertEqual(env["RAM_GB"], "64")
        self.assertEqual(env["CTX"], "4096")
        self.assertEqual(env["COLI_V4_NO_DSPARK"], "1")
        self.assertEqual(
            env["COLI_V4_DSPARK_MODEL"], os.path.abspath("relative-dspark")
        )

    def test_v4_run_forwards_dspark_flags(self):
        directory, root = self.make_model()
        try:
            engine = root / ("deepseek_v4.exe" if os.name == "nt" else "deepseek_v4")
            engine.write_bytes(b"")
            draft = root / "dspark"
            draft.mkdir()
            args = argparse.Namespace(
                model=str(root),
                prompt=["hello", "world"],
                ngen=10,
                ram=64,
                ctx=0,
                temp=None,
                no_dspark=True,
                draft_model=str(draft),
            )
            with mock.patch.object(self.cli, "engine_for", return_value=str(engine)), \
                    mock.patch.object(self.cli, "banner"), \
                    mock.patch.object(self.cli.subprocess, "call", return_value=0) as call:
                with self.assertRaises(SystemExit) as exited:
                    self.cli.cmd_run(args)
            self.assertEqual(exited.exception.code, 0)
            command = call.call_args.args[0]
            self.assertEqual(command[1:5], [str(root), "hello world", "--max-tokens", "10"])
            self.assertIn("--no-dspark", command)
            self.assertEqual(command[-2:], ["--draft-model", str(draft.resolve())])
        finally:
            directory.cleanup()

    def test_openai_renderer_uses_native_v4_multiturn_template(self):
        import openai_server

        prompt = openai_server.render_chat_v4(
            [
                {"role": "system", "content": "Be concise."},
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi!"},
                {"role": "user", "content": "Again"},
            ],
            enable_thinking=True,
        )
        self.assertEqual(
            prompt,
            "<\uff5cbegin\u2581of\u2581sentence\uff5c>Be concise."
            "<\uff5cUser\uff5c>Hello<\uff5cAssistant\uff5c></think>Hi!"
            "<\uff5cend\u2581of\u2581sentence\uff5c>"
            "<\uff5cUser\uff5c>Again<\uff5cAssistant\uff5c><think>",
        )

    def test_openai_renderer_rejects_unwired_tools(self):
        import openai_server

        with self.assertRaises(openai_server.APIError):
            openai_server.render_chat_v4(
                [{"role": "user", "content": "hello"}],
                tools=[{"type": "function"}],
            )


if __name__ == "__main__":
    unittest.main()
