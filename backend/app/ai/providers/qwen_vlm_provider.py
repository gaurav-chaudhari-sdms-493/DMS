"""T90 — local VLM provider scaffold: Qwen2.5-VL-7B-Instruct.

╔══════════════════════════════════════════════════════════════════════╗
║  UNTESTED. UNVERIFIED. NEVER INSTANTIATED OR RUN.                     ║
║                                                                        ║
║  This class was written without a GPU available (backlog A2 — "GPU    ║
║  availability for the local VLM, at least one 24 GB card for          ║
║  development" — not available in this dev environment: 4 CPU cores,  ║
║  ~14GB RAM, no GPU). Qwen2.5-VL-7B needs ~15GB+ VRAM to run at usable ║
║  speed; CPU inference would take minutes per page and could not be    ║
║  meaningfully verified here in reasonable time.                       ║
║                                                                        ║
║  This is a real starting point — correct imports, a plausible model   ║
║  loading + inference shape matching how the transformers library's    ║
║  Qwen2.5-VL support works — not a stub or placeholder. But it has     ║
║  NEVER been run, so treat every detail (dtype, prompt template,       ║
║  generation kwargs, output parsing) as unverified until someone with  ║
║  real GPU hardware actually exercises it against a real page image.   ║
║                                                                        ║
║  NOT wired into app/ai/factory.py's get_vlm_provider() active         ║
║  resolution path — 'qwen_local' is deliberately not a selectable      ║
║  ai_vlm_provider config value, so it can't be silently chosen and     ║
║  fail confusingly in production. Wiring it in is follow-up work for   ║
║  whoever has the GPU to actually validate this against real documents.║
╚══════════════════════════════════════════════════════════════════════╝

Matches the existing VLMProvider interface (app/ai/base.py) and the
calling convention GeminiVLMProvider already establishes — one page
image + one instruction prompt in, one raw text response out (expected
to be JSON per the prompt's own contract, same as every other VLM
provider here).
"""

from app.ai.base import VLMProvider


class QwenVLMProvider(VLMProvider):
    def __init__(self, model_name: str = "Qwen/Qwen2.5-VL-7B-Instruct", device: str = "cuda"):
        self.model_name = model_name
        self.device = device
        self._model = None
        self._processor = None

    def _load(self):
        """Lazy load — the 7B weights (~15GB) shouldn't be pulled into
        memory until the provider is actually used. UNVERIFIED: this
        loading shape follows transformers' documented Qwen2.5-VL usage
        pattern at the time this was written, but has never actually
        been run against real weights in this codebase."""
        import torch
        from transformers import Qwen2_5_VLForConditionalGeneration, AutoProcessor

        self._model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            self.model_name,
            torch_dtype=torch.bfloat16,
            device_map=self.device,
        )
        self._processor = AutoProcessor.from_pretrained(self.model_name)

    async def extract_structured(self, image_bytes: bytes, prompt: str) -> str:
        """UNVERIFIED end to end. Runs the model synchronously in-process
        (no async inference API exists for local transformers models) —
        a real integration would need asyncio.to_thread(...) here to
        avoid blocking the event loop, same as PdfPlumberProvider does
        for its synchronous work. Left out of this scaffold since
        wrapping untested inference logic in a thread doesn't make the
        inference logic itself any more verified."""
        import io
        from PIL import Image

        if self._model is None:
            self._load()

        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        messages = [{
            "role": "user",
            "content": [
                {"type": "image", "image": image},
                {"type": "text", "text": prompt},
            ],
        }]

        text_input = self._processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self._processor(
            text=[text_input], images=[image], return_tensors="pt"
        ).to(self._model.device)

        generated_ids = self._model.generate(**inputs, max_new_tokens=2048)
        generated_ids_trimmed = [
            out_ids[len(in_ids):]
            for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        output_text = self._processor.batch_decode(
            generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )
        return output_text[0] if output_text else ""
