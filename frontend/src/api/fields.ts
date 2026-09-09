/** Русские названия полей — используются в форме карточки и при разборе ошибок валидации. */
export const FIELD_LABELS: Record<string, string> = {
  last_name: 'Фамилия',
  first_name: 'Имя',
  middle_name: 'Отчество',
  phone: 'Телефон',
  email: 'E-mail',
  property_info: 'Сведения об имуществе',
  comment: 'Комментарий',
  text: 'Текст комментария',
  login: 'Логин',
  password: 'Пароль',
};

export const fieldLabel = (name: string): string => FIELD_LABELS[name] ?? name;
