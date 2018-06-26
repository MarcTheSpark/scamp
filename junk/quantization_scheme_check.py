# This allows the user to simply give a time signature as a quantization_scheme.
if not isinstance(quantization_scheme, QuantizationScheme):
    if not isinstance(quantization_scheme, (TimeSignature, str, tuple)):
        raise ValueError("Uninterpretable quantization_scheme")
    elif isinstance(quantization_scheme, TimeSignature):
        time_signature = quantization_scheme
    else:
        try:
            if isinstance(quantization_scheme, str):
                time_signature = TimeSignature.from_string(quantization_scheme)
            else:
                time_signature = TimeSignature(*quantization_scheme)
        except Exception:
            raise ValueError("Uninterpretable quantization_scheme")
    quantization_scheme = QuantizationScheme.from_time_signature(time_signature)