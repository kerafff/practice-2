CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);


CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    fio VARCHAR(255) NOT NULL,
    phone VARCHAR(50),
    login VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(100) NOT NULL,
    role_id INTEGER NOT NULL REFERENCES roles(id)
);


CREATE TABLE request_statuses (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE
);


CREATE TABLE requests (
    id SERIAL PRIMARY KEY,

    start_date DATE NOT NULL DEFAULT CURRENT_DATE,

    climate_tech_type VARCHAR(100) NOT NULL,
    climate_tech_model VARCHAR(150) NOT NULL,
    problem_description TEXT NOT NULL,

    status_id INTEGER NOT NULL REFERENCES request_statuses(id),

    client_id INTEGER NOT NULL REFERENCES users(id),
    master_id INTEGER REFERENCES users(id),

    completion_date DATE,
    extended_due_date DATE
);


CREATE TABLE parts (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL UNIQUE
);


CREATE TABLE request_parts (
    id SERIAL PRIMARY KEY,
    request_id INTEGER NOT NULL REFERENCES requests(id) ON DELETE CASCADE,
    part_id INTEGER NOT NULL REFERENCES parts(id) ON DELETE CASCADE,
    quantity INTEGER NOT NULL DEFAULT 1
);


CREATE TABLE comments (
    id SERIAL PRIMARY KEY,
    request_id INTEGER NOT NULL REFERENCES requests(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE INDEX idx_users_role_id ON users(role_id);

CREATE INDEX idx_requests_client_id ON requests(client_id);
CREATE INDEX idx_requests_master_id ON requests(master_id);
CREATE INDEX idx_requests_status_id ON requests(status_id);

CREATE INDEX idx_request_parts_request_id ON request_parts(request_id);
CREATE INDEX idx_request_parts_part_id ON request_parts(part_id);

CREATE INDEX idx_comments_request_id ON comments(request_id);
