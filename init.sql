-- Project 04: Employee Directory Portal Database Schema
CREATE TABLE IF NOT EXISTS employees (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    role VARCHAR(100) NOT NULL,
    department VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    photo_path VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Seed initial employee records with specialized avatars
INSERT INTO employees (name, role, department, email, photo_path) VALUES
    ('Sarah Connor', 'Principal Site Reliability Engineer', 'Engineering', 'sarah.connor@cyberdyne.internal', '/static/img/avatar-sarah.svg'),
    ('Alex Chen', 'Lead UI/UX Designer', 'Design', 'alex.chen@designlab.internal', '/static/img/avatar-alex.svg'),
    ('Marcus Vance', 'Cloud Infrastructure Architect', 'Engineering', 'marcus.v@cloudops.internal', '/static/img/avatar-marcus.svg'),
    ('Priya Patel', 'Head of People Operations', 'Human Resources', 'priya.patel@workplace.internal', '/static/img/avatar-priya.svg'),
    ('Elena Rostova', 'Senior DevOps Engineer', 'Engineering', 'elena.rostova@devops.internal', '/static/img/avatar-elena.svg'),
    ('Liam Tanaka', 'Staff Product Manager', 'Product', 'liam.tanaka@product.internal', '/static/img/avatar-liam.svg')
ON CONFLICT (email) DO NOTHING;
