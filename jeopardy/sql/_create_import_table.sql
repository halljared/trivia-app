DROP TABLE IF EXISTS public.import_table;
CREATE TABLE public.import_table
(
    id serial,
    round smallint,
    clue_value smallint,
    daily_double_value smallint,
    category character varying(256),
    comments text,
    answer text,
    question text,
    air_date character varying(32),
    notes text,
    PRIMARY KEY (id)
);
