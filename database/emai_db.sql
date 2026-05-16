-- ============================================================
--  EMAI-APP — Base de datos completa
--  MySQL Workbench
--  Versión 1.0.0
-- ============================================================

-- ─── CREAR Y SELECCIONAR BASE DE DATOS ───────────────────────────────────────
CREATE DATABASE IF NOT EXISTS emai_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE emai_db;

-- ─── DESACTIVAR FK CHECKS DURANTE CREACIÓN ───────────────────────────────────
SET FOREIGN_KEY_CHECKS = 0;

-- ============================================================
--  TABLA: institutions
-- ============================================================
CREATE TABLE IF NOT EXISTS institutions (
    id                      CHAR(36)        NOT NULL,
    name                    VARCHAR(200)    NOT NULL,
    primary_color           VARCHAR(7)      NOT NULL DEFAULT '#1A3C5E',
    secondary_color         VARCHAR(7)      NOT NULL DEFAULT '#2E6DA4',
    logo_url                VARCHAR(500)    NULL,
    data_terms_accepted     TINYINT(1)      NOT NULL DEFAULT 0,
    data_terms_accepted_at  DATETIME        NULL,
    data_terms_accepted_by  CHAR(36)        NULL,
    created_at              DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
                                            ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
--  TABLA: users
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id              CHAR(36)        NOT NULL,
    username        VARCHAR(80)     NOT NULL,
    password_hash   VARCHAR(255)    NOT NULL,
    full_name       VARCHAR(200)    NOT NULL,
    role            ENUM('admin','directivo','docente') NOT NULL,
    sub_role        ENUM('director','subdirector','coordinador','psicologo','otro') NULL,
    photo_url       VARCHAR(500)    NULL,
    institution_id  CHAR(36)        NULL,
    course_id       CHAR(36)        NULL,
    is_active       TINYINT(1)      NOT NULL DEFAULT 1,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
                                    ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_username (username),
    INDEX idx_role (role),
    INDEX idx_institution (institution_id),
    INDEX idx_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
--  TABLA: access_tokens
-- ============================================================
CREATE TABLE IF NOT EXISTS access_tokens (
    id               CHAR(36)        NOT NULL,
    token            VARCHAR(30)     NOT NULL,
    institution_name VARCHAR(200)    NULL,
    institution_id   CHAR(36)        NULL,
    used             TINYINT(1)      NOT NULL DEFAULT 0,
    used_at          DATETIME        NULL,
    used_by          CHAR(36)        NULL,
    created_by       CHAR(36)        NOT NULL,
    expires_at       DATETIME        NULL,
    created_at       DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_token (token),
    INDEX idx_used (used),
    INDEX idx_created_by (created_by)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
--  TABLA: courses
-- ============================================================
CREATE TABLE IF NOT EXISTS courses (
    id              CHAR(36)        NOT NULL,
    name            VARCHAR(20)     NOT NULL,
    grade           VARCHAR(10)     NOT NULL,
    `group`         VARCHAR(10)     NOT NULL,
    institution_id  CHAR(36)        NOT NULL,
    teacher_id      CHAR(36)        NULL,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_institution (institution_id),
    INDEX idx_teacher (teacher_id),
    UNIQUE KEY uq_course_inst (institution_id, grade, `group`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
--  TABLA: subjects
-- ============================================================
CREATE TABLE IF NOT EXISTS subjects (
    id              CHAR(36)        NOT NULL,
    name            VARCHAR(100)    NOT NULL,
    base_type       VARCHAR(30)     NOT NULL DEFAULT 'matematicas',
    institution_id  CHAR(36)        NOT NULL,
    course_id       CHAR(36)        NULL,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_institution (institution_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
--  TABLA: students
-- ============================================================
CREATE TABLE IF NOT EXISTS students (
    id              CHAR(36)        NOT NULL,
    full_name       VARCHAR(200)    NOT NULL,
    photo_url       VARCHAR(500)    NULL,
    course_id       CHAR(36)        NOT NULL,
    institution_id  CHAR(36)        NOT NULL,
    created_by_id   CHAR(36)        NOT NULL,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
                                    ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_course (course_id),
    INDEX idx_institution (institution_id),
    INDEX idx_created_by (created_by_id),
    INDEX idx_full_name (full_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
--  TABLA: exams
-- ============================================================
CREATE TABLE IF NOT EXISTS exams (
    id              CHAR(36)        NOT NULL,
    name            VARCHAR(300)    NOT NULL,
    course_id       CHAR(36)        NOT NULL,
    subject_id      CHAR(36)        NULL,
    teacher_id      CHAR(36)        NOT NULL,
    institution_id  CHAR(36)        NOT NULL,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
                                    ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_course (course_id),
    INDEX idx_teacher (teacher_id),
    INDEX idx_institution (institution_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
--  TABLA: exam_results
-- ============================================================
CREATE TABLE IF NOT EXISTS exam_results (
    id              CHAR(36)        NOT NULL,
    exam_id         CHAR(36)        NOT NULL,
    student_id      CHAR(36)        NOT NULL,
    image_urls      TEXT            NULL        COMMENT 'JSON array de URLs de imágenes',
    ocr_raw_text    LONGTEXT        NULL        COMMENT 'Texto crudo extraído por OCR',
    problems_json   LONGTEXT        NULL        COMMENT 'JSON array de ExamProblem',
    final_score     DECIMAL(3,1)    NULL        COMMENT 'Nota 1.0 a 5.0',
    grade_color     VARCHAR(10)     NULL        COMMENT 'green o red',
    teacher_notes   TEXT            NULL,
    status          ENUM('pending','processing','reviewed','graded')
                                    NOT NULL DEFAULT 'pending',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
                                    ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_exam (exam_id),
    INDEX idx_student (student_id),
    INDEX idx_status (status),
    INDEX idx_score (final_score),
    UNIQUE KEY uq_exam_student (exam_id, student_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
--  TABLA: support_messages
-- ============================================================
CREATE TABLE IF NOT EXISTS support_messages (
    id              CHAR(36)        NOT NULL,
    from_user_id    CHAR(36)        NOT NULL,
    from_username   VARCHAR(80)     NOT NULL,
    from_role       VARCHAR(20)     NOT NULL,
    institution_id  CHAR(36)        NULL,
    message         TEXT            NOT NULL,
    `read`          TINYINT(1)      NOT NULL DEFAULT 0,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_read (`read`),
    INDEX idx_from_user (from_user_id),
    INDEX idx_institution (institution_id),
    INDEX idx_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
--  CLAVES FORÁNEAS
-- ============================================================

-- institutions
ALTER TABLE institutions
    ADD CONSTRAINT fk_inst_accepted_by
        FOREIGN KEY (data_terms_accepted_by) REFERENCES users(id)
        ON DELETE SET NULL ON UPDATE CASCADE;

-- users
ALTER TABLE users
    ADD CONSTRAINT fk_user_institution
        FOREIGN KEY (institution_id) REFERENCES institutions(id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    ADD CONSTRAINT fk_user_course
        FOREIGN KEY (course_id) REFERENCES courses(id)
        ON DELETE SET NULL ON UPDATE CASCADE;

-- access_tokens
ALTER TABLE access_tokens
    ADD CONSTRAINT fk_token_institution
        FOREIGN KEY (institution_id) REFERENCES institutions(id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    ADD CONSTRAINT fk_token_creator
        FOREIGN KEY (created_by) REFERENCES users(id)
        ON DELETE RESTRICT ON UPDATE CASCADE;

-- courses
ALTER TABLE courses
    ADD CONSTRAINT fk_course_institution
        FOREIGN KEY (institution_id) REFERENCES institutions(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    ADD CONSTRAINT fk_course_teacher
        FOREIGN KEY (teacher_id) REFERENCES users(id)
        ON DELETE SET NULL ON UPDATE CASCADE;

-- subjects
ALTER TABLE subjects
    ADD CONSTRAINT fk_subject_institution
        FOREIGN KEY (institution_id) REFERENCES institutions(id)
        ON DELETE CASCADE ON UPDATE CASCADE;

-- students
ALTER TABLE students
    ADD CONSTRAINT fk_student_course
        FOREIGN KEY (course_id) REFERENCES courses(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    ADD CONSTRAINT fk_student_institution
        FOREIGN KEY (institution_id) REFERENCES institutions(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    ADD CONSTRAINT fk_student_created_by
        FOREIGN KEY (created_by_id) REFERENCES users(id)
        ON DELETE RESTRICT ON UPDATE CASCADE;

-- exams
ALTER TABLE exams
    ADD CONSTRAINT fk_exam_course
        FOREIGN KEY (course_id) REFERENCES courses(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    ADD CONSTRAINT fk_exam_subject
        FOREIGN KEY (subject_id) REFERENCES subjects(id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    ADD CONSTRAINT fk_exam_teacher
        FOREIGN KEY (teacher_id) REFERENCES users(id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    ADD CONSTRAINT fk_exam_institution
        FOREIGN KEY (institution_id) REFERENCES institutions(id)
        ON DELETE CASCADE ON UPDATE CASCADE;

-- exam_results
ALTER TABLE exam_results
    ADD CONSTRAINT fk_result_exam
        FOREIGN KEY (exam_id) REFERENCES exams(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    ADD CONSTRAINT fk_result_student
        FOREIGN KEY (student_id) REFERENCES students(id)
        ON DELETE CASCADE ON UPDATE CASCADE;

-- support_messages
ALTER TABLE support_messages
    ADD CONSTRAINT fk_msg_user
        FOREIGN KEY (from_user_id) REFERENCES users(id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    ADD CONSTRAINT fk_msg_institution
        FOREIGN KEY (institution_id) REFERENCES institutions(id)
        ON DELETE SET NULL ON UPDATE CASCADE;

-- ─── REACTIVAR FK CHECKS ──────────────────────────────────────────────────────
SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================
--  DATOS INICIALES: primer administrador del sistema
--  Usuario: admin  |  Contraseña: admin123
--  (bcrypt hash de "admin123")
-- ============================================================
INSERT IGNORE INTO users (
    id, username, password_hash, full_name, role, is_active, created_at, updated_at
) VALUES (
    'a0000000-0000-0000-0000-000000000001',
    'admin',
    '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW',
    'Administrador EMAI',
    'admin',
    1,
    NOW(),
    NOW()
);

-- ============================================================
--  VISTAS ÚTILES
-- ============================================================

-- Vista: resumen de exámenes por estudiante
CREATE OR REPLACE VIEW v_student_exam_summary AS
SELECT
    s.id                            AS student_id,
    s.full_name                     AS student_name,
    c.name                          AS course_name,
    COUNT(er.id)                    AS total_exams,
    COUNT(CASE WHEN er.final_score >= 3.0 THEN 1 END) AS passed,
    COUNT(CASE WHEN er.final_score < 3.0
               AND er.final_score IS NOT NULL THEN 1 END) AS failed,
    ROUND(AVG(er.final_score), 2)   AS average_score,
    s.institution_id
FROM students s
JOIN courses c        ON c.id = s.course_id
LEFT JOIN exam_results er ON er.student_id = s.id
GROUP BY s.id, s.full_name, c.name, s.institution_id;

-- Vista: resumen por curso
CREATE OR REPLACE VIEW v_course_summary AS
SELECT
    c.id                            AS course_id,
    c.name                          AS course_name,
    c.grade,
    c.group,
    c.institution_id,
    u.full_name                     AS teacher_name,
    COUNT(DISTINCT s.id)            AS total_students,
    COUNT(DISTINCT e.id)            AS total_exams,
    ROUND(AVG(er.final_score), 2)   AS avg_score
FROM courses c
LEFT JOIN users u           ON u.id = c.teacher_id
LEFT JOIN students s        ON s.course_id = c.id
LEFT JOIN exams e           ON e.course_id = c.id
LEFT JOIN exam_results er   ON er.exam_id = e.id
GROUP BY c.id, c.name, c.grade, c.group, c.institution_id, u.full_name;

-- Vista: tokens disponibles
CREATE OR REPLACE VIEW v_available_tokens AS
SELECT
    id,
    token,
    institution_name,
    created_at,
    expires_at
FROM access_tokens
WHERE used = 0
  AND (expires_at IS NULL OR expires_at > NOW());

-- Vista: mensajes de soporte sin leer
CREATE OR REPLACE VIEW v_unread_support AS
SELECT
    sm.id,
    sm.from_username,
    sm.from_role,
    i.name          AS institution_name,
    sm.message,
    sm.created_at
FROM support_messages sm
LEFT JOIN institutions i ON i.id = sm.institution_id
WHERE sm.read = 0
ORDER BY sm.created_at DESC;

-- ============================================================
--  PROCEDIMIENTOS ALMACENADOS
-- ============================================================

DELIMITER $$

-- Estadísticas generales de una institución
CREATE PROCEDURE IF NOT EXISTS sp_institution_stats(IN p_institution_id CHAR(36))
BEGIN
    SELECT
        (SELECT COUNT(*) FROM users
         WHERE institution_id = p_institution_id
           AND role = 'directivo' AND is_active = 1)     AS total_directivos,
        (SELECT COUNT(*) FROM users
         WHERE institution_id = p_institution_id
           AND role = 'docente' AND is_active = 1)        AS total_docentes,
        (SELECT COUNT(*) FROM courses
         WHERE institution_id = p_institution_id)          AS total_cursos,
        (SELECT COUNT(*) FROM students
         WHERE institution_id = p_institution_id)          AS total_estudiantes,
        (SELECT COUNT(*) FROM exams
         WHERE institution_id = p_institution_id)          AS total_examenes,
        (SELECT ROUND(AVG(er.final_score), 2)
         FROM exam_results er
         JOIN exams ex ON ex.id = er.exam_id
         WHERE ex.institution_id = p_institution_id
           AND er.final_score IS NOT NULL)                  AS promedio_general;
END$$

-- Reportes de un docente
CREATE PROCEDURE IF NOT EXISTS sp_teacher_report(IN p_teacher_id CHAR(36))
BEGIN
    SELECT
        e.name                              AS exam_name,
        c.name                              AS course_name,
        s.full_name                         AS student_name,
        er.final_score,
        er.grade_color,
        er.status,
        er.created_at
    FROM exam_results er
    JOIN exams e    ON e.id = er.exam_id
    JOIN courses c  ON c.id = e.course_id
    JOIN students s ON s.id = er.student_id
    WHERE e.teacher_id = p_teacher_id
    ORDER BY er.created_at DESC;
END$$

-- Limpiar tokens expirados
CREATE PROCEDURE IF NOT EXISTS sp_cleanup_expired_tokens()
BEGIN
    DELETE FROM access_tokens
    WHERE used = 0
      AND expires_at IS NOT NULL
      AND expires_at < NOW();

    SELECT ROW_COUNT() AS deleted_tokens;
END$$

DELIMITER ;

-- ============================================================
--  DATOS DE PRUEBA (comentar en producción)
-- ============================================================

-- Institución de prueba
INSERT IGNORE INTO institutions (
    id, name, primary_color, secondary_color,
    data_terms_accepted, data_terms_accepted_at, created_at, updated_at
) VALUES (
    'b0000000-0000-0000-0000-000000000001',
    'I.E. Colegio Demo',
    '#1A3C5E',
    '#2E6DA4',
    1,
    NOW(),
    NOW(),
    NOW()
);

-- Directivo de prueba (contraseña: director123)
INSERT IGNORE INTO users (
    id, username, password_hash, full_name, role, sub_role,
    institution_id, is_active, created_at, updated_at
) VALUES (
    'c0000000-0000-0000-0000-000000000001',
    'directivo_demo',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMeSSi61zONEa7Z8BEjRomGkAi',
    'Director Demo',
    'directivo',
    'director',
    'b0000000-0000-0000-0000-000000000001',
    1,
    NOW(),
    NOW()
);

-- Docente de prueba (contraseña: docente123)
INSERT IGNORE INTO users (
    id, username, password_hash, full_name, role,
    institution_id, is_active, created_at, updated_at
) VALUES (
    'd0000000-0000-0000-0000-000000000001',
    'docente_demo',
    '$2b$12$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC__wF2tBCon96A.wzXuJ',
    'Docente Demo',
    'docente',
    'b0000000-0000-0000-0000-000000000001',
    1,
    NOW(),
    NOW()
);

-- Cursos de prueba
INSERT IGNORE INTO courses (id, name, grade, `group`, institution_id, teacher_id, created_at)
VALUES
    ('e0000000-0000-0000-0000-000000000001', '2-1', '2', '1', 'b0000000-0000-0000-0000-000000000001', 'd0000000-0000-0000-0000-000000000001', NOW()),
    ('e0000000-0000-0000-0000-000000000002', '3-2', '3', '2', 'b0000000-0000-0000-0000-000000000001', 'd0000000-0000-0000-0000-000000000001', NOW()),
    ('e0000000-0000-0000-0000-000000000003', '4-1', '4', '1', 'b0000000-0000-0000-0000-000000000001', NULL, NOW());

-- Materia de prueba
INSERT IGNORE INTO subjects (id, name, base_type, institution_id, created_at)
VALUES
    ('f0000000-0000-0000-0000-000000000001', 'Matemáticas', 'matematicas', 'b0000000-0000-0000-0000-000000000001', NOW()),
    ('f0000000-0000-0000-0000-000000000002', 'Geometría',   'matematicas', 'b0000000-0000-0000-0000-000000000001', NOW());

-- Actualizar curso_id del docente demo
UPDATE users SET course_id = 'e0000000-0000-0000-0000-000000000001'
WHERE id = 'd0000000-0000-0000-0000-000000000001';

-- Estudiantes de prueba
INSERT IGNORE INTO students (id, full_name, course_id, institution_id, created_by_id, created_at, updated_at)
VALUES
    ('g0000000-0000-0000-0000-000000000001', 'Ana María García',     'e0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000001', 'd0000000-0000-0000-0000-000000000001', NOW(), NOW()),
    ('g0000000-0000-0000-0000-000000000002', 'Carlos Pérez López',   'e0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000001', 'd0000000-0000-0000-0000-000000000001', NOW(), NOW()),
    ('g0000000-0000-0000-0000-000000000003', 'Luisa Fernanda Torres','e0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000001', 'd0000000-0000-0000-0000-000000000001', NOW(), NOW()),
    ('g0000000-0000-0000-0000-000000000004', 'Miguel Rodríguez',     'e0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000001', 'd0000000-0000-0000-0000-000000000001', NOW(), NOW()),
    ('g0000000-0000-0000-0000-000000000005', 'Valentina Morales',    'e0000000-0000-0000-0000-000000000001', 'b0000000-0000-0000-0000-000000000001', 'd0000000-0000-0000-0000-000000000001', NOW(), NOW());

-- Token de prueba disponible
INSERT IGNORE INTO access_tokens (id, token, institution_name, used, created_by, created_at)
VALUES (
    'h0000000-0000-0000-0000-000000000001',
    'EMAI-TEST-0001',
    'Institución de Prueba',
    0,
    'a0000000-0000-0000-0000-000000000001',
    NOW()
);

-- ============================================================
--  VERIFICACIÓN FINAL
-- ============================================================
SELECT 'Tablas creadas:' AS info;
SELECT TABLE_NAME, TABLE_ROWS
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'emai_db'
  AND TABLE_TYPE = 'BASE TABLE'
ORDER BY TABLE_NAME;

SELECT 'Vistas creadas:' AS info;
SELECT TABLE_NAME AS vista_name
FROM information_schema.VIEWS
WHERE TABLE_SCHEMA = 'emai_db';

SELECT 'Usuarios iniciales:' AS info;
SELECT id, username, role, full_name, is_active FROM users;
