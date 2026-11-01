export interface AuthMethodsInterface {
  googleSso: boolean;
  microsoftSso: boolean;
  passwordLogin: boolean;
}

export function createDefaultAuthMethods(): AuthMethodsInterface {
  return {
    googleSso: false,
    microsoftSso: false,
    passwordLogin: true,
  };
}
