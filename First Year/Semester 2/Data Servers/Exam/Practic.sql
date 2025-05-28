/*
Requirement:
- Create table Autobus [id, model, brand, chassis_series, seat_count, fuel_consumption] with integrity constraints (primary key, unique, CHECK constraints)
- Add comments to the table and columns
- Populate the table with at least 10 records
- Procedure that accepts seat_count as a parameter and returns the first 3 buses per brand, ordered by ascending fuel_consumption, where seat_count < parameter
- Function that displays bus models with more than 30 seats, and for those with fuel_consumption >= 30, outputs a message via user-defined exception handling
*/

-- 1. Create table Autobus with constraints
CREATE TABLE Autobus
(
    id               NUMBER PRIMARY KEY,
    model            VARCHAR2(50)        NOT NULL,
    brand            VARCHAR2(50)        NOT NULL,
    chassis_series   VARCHAR2(20) UNIQUE NOT NULL,
    seat_count       NUMBER              NOT NULL CHECK (seat_count > 0),
    fuel_consumption NUMBER(5, 2)        NOT NULL CHECK (fuel_consumption > 0)
);

-- 2. Add comments to table and columns
COMMENT ON TABLE Autobus IS 'Information about the company''s buses';
COMMENT ON COLUMN Autobus.id IS 'Unique identifier of the bus';
COMMENT ON COLUMN Autobus.model IS 'Model name of the bus';
COMMENT ON COLUMN Autobus.brand IS 'Manufacturer of the bus';
COMMENT ON COLUMN Autobus.chassis_series IS 'Vehicle identification number (VIN) of the chassis';
COMMENT ON COLUMN Autobus.seat_count IS 'Total number of seats';
COMMENT ON COLUMN Autobus.fuel_consumption IS 'Average fuel consumption (L/100km)';

-- 3. Populate the table with at least 10 records
INSERT INTO Autobus (id, model, brand, chassis_series, seat_count, fuel_consumption) VALUES (1, 'CityStar', 'Mercedes', 'MB1234567890', 40, 25.5);
INSERT INTO Autobus (id, model, brand, chassis_series, seat_count, fuel_consumption) VALUES (2, 'Tourismo', 'Mercedes', 'MB0987654321', 50, 28.0);
INSERT INTO Autobus (id, model, brand, chassis_series, seat_count, fuel_consumption) VALUES (3, 'InterCity', 'Volvo', 'VL1122334455', 55, 30.2);
INSERT INTO Autobus (id, model, brand, chassis_series, seat_count, fuel_consumption) VALUES (4, 'B7R', 'Volvo', 'VL5566778899', 45, 27.0);
INSERT INTO Autobus (id, model, brand, chassis_series, seat_count, fuel_consumption) VALUES (5, 'MetroLine', 'Scania', 'SC1234567890', 60, 22.5);
INSERT INTO Autobus (id, model, brand, chassis_series, seat_count, fuel_consumption) VALUES (6, 'CityLink', 'Scania', 'SC0987654321', 35, 24.0);
INSERT INTO Autobus (id, model, brand, chassis_series, seat_count, fuel_consumption) VALUES (7, 'MegaBus', 'Volvo', 'VL1122334456', 70, 32.0);
INSERT INTO Autobus (id, model, brand, chassis_series, seat_count, fuel_consumption) VALUES (8, 'EcoCity', 'Mercedes', 'MB1234567891', 30, 20.0);
INSERT INTO Autobus (id, model, brand, chassis_series, seat_count, fuel_consumption) VALUES (9, 'UrbanStar', 'Scania', 'SC0987654322', 25, 18.5);
INSERT INTO Autobus (id, model, brand, chassis_series, seat_count, fuel_consumption) VALUES (10, 'CityCruiser', 'Mercedes', 'MB1122334457', 40, 26.0);
COMMIT;

-- 4. Procedure: Get top 3 buses per brand with seat_count < parameter
CREATE OR REPLACE PROCEDURE GetTop3BusesByBrand(
    p_seat_count IN NUMBER,
    p_cursor_out OUT SYS_REFCURSOR
) AS
BEGIN
    OPEN p_cursor_out FOR
        SELECT id, model, brand, chassis_series, seat_count, fuel_consumption
        FROM (SELECT b.*, ROW_NUMBER() OVER (PARTITION BY b.brand ORDER BY b.fuel_consumption) AS rn
              FROM Autobus b WHERE b.seat_count < p_seat_count)
        WHERE rn <= 3 ORDER BY brand, fuel_consumption;
END GetTop3BusesByBrand;

-- Example of how to call the procedure
DECLARE
  v_cursor   SYS_REFCURSOR;
  v_id        NUMBER;
  v_model     VARCHAR2(50);
  v_brand     VARCHAR2(50);
  v_series    VARCHAR2(20);
  v_seat      NUMBER;
  v_consum    NUMBER(5,2);
BEGIN
  -- 1. Open the cursor via your procedure
  GetTop3BusesByBrand(40, v_cursor);

  -- 2. Loop to fetch all rows
  LOOP
    FETCH v_cursor
      INTO v_id, v_model, v_brand, v_series, v_seat, v_consum;
    EXIT WHEN v_cursor%NOTFOUND;

    -- 3. Display each row
    DBMS_OUTPUT.PUT_LINE('ID='||v_id||', Model='||v_model||', Brand='||v_brand||', Seats='||v_seat||', Consumption='||v_consum);
  END LOOP;

  -- 4. Close the cursor
  CLOSE v_cursor;
END;

-- 5. Function with user-defined exception for high consumption
CREATE OR REPLACE FUNCTION DisplayModelsWithCheck
    RETURN VARCHAR2
AS
    CURSOR bus_cursor IS
        SELECT model, fuel_consumption FROM Autobus WHERE seat_count > 30;
    v_model  VARCHAR2(50);
    v_consum NUMBER(5, 2);
    ex_high_consumption EXCEPTION;
BEGIN
    FOR rec IN bus_cursor
        LOOP
            v_model := rec.model;
            v_consum := rec.fuel_consumption;
            BEGIN
                IF v_consum < 30 THEN
                    DBMS_OUTPUT.PUT_LINE('Model OK: ' || v_model || ' (consumption ' || v_consum || ')');
                ELSE
                    RAISE ex_high_consumption;
                END IF;
            EXCEPTION
                WHEN ex_high_consumption THEN
                    DBMS_OUTPUT.PUT_LINE('Warning: Bus model ' || v_model || ' has high consumption: ' || v_consum);
            END;
        END LOOP;
    RETURN 'Processing completed.';
END DisplayModelsWithCheck;

-- Example of how to call the function
DECLARE
  v_result VARCHAR2(100);
BEGIN
  v_result := DisplayModelsWithCheck();
  DBMS_OUTPUT.PUT_LINE(v_result);
END;