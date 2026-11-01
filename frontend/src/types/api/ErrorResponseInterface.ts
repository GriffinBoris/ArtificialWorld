export interface ErrorItemInterface {
  attr?: string;
  code?: string;
  detail: string;
}

export interface ErrorResponseInterface {
  errors?: ErrorItemInterface[];
}
