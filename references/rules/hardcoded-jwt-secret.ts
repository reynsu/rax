// ruleid: rax.sec.hardcoded-jwt-secret
const apiKey = "EXAMPLE_FAKE_VALUE_FOR_TESTING_abcdef0123";

// ok: rax.sec.hardcoded-jwt-secret
const apiKey2 = process.env.STRIPE_API_KEY;

export { apiKey, apiKey2 };
