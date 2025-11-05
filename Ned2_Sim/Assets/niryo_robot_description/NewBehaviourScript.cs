using System.Collections;
using System.Collections.Generic;
using UnityEngine;


public class NedController : MonoBehaviour
{
    [Header("Assign in Inspector")]
    public List<ArticulationBody> joints; // 6 DOF, en orden
    public Transform endEffector;         // referencia al TCP o ultimo link

    [Header("Motion params")]
    public float defaultVelDeg = 30f;     // deg/s
    public float defaultAccDeg = 120f;    // deg/s^2
    public float toleranceDeg = 0.5f;

    private bool executing;
    private float timeInMotion;
    private float tMax;
    private float[] qStart, qGoal;

    void FixedUpdate()
    {
        if (!executing) return;
        timeInMotion += Time.fixedDeltaTime;
        float t = Mathf.Min(timeInMotion, tMax);

        var qCmd = new float[joints.Count];
        for (int i = 0; i < joints.Count; i++)
        {
            qCmd[i] = TrapezoidPosition(t, qStart[i], qGoal[i], defaultVelDeg, defaultAccDeg);
        }
        ApplyJointTargets(qCmd);

        if (AllClose(qCmd, qGoal, toleranceDeg) || timeInMotion >= tMax)
        {
            executing = false;
        }
    }

    public void MoveJ(float[] qDegTarget, float velDeg = -1f, float accDeg = -1f)
    {
        if (velDeg > 0) defaultVelDeg = velDeg;
        if (accDeg > 0) defaultAccDeg = accDeg;

        qStart = ReadCurrentQDeg();
        qGoal = (float[])qDegTarget.Clone();
        timeInMotion = 0f;

        tMax = 0f;
        for (int i = 0; i < joints.Count; i++)
        {
            float dq = Mathf.Abs(Mathf.DeltaAngle(qStart[i], qGoal[i]));
            float t = TrapezoidDuration(dq, defaultVelDeg, defaultAccDeg);
            if (t > tMax) tMax = t;
        }
        executing = true;
    }

    public void Jog(int jointIndex, float deltaDeg)
    {
        var q = ReadCurrentQDeg();
        q[jointIndex] = q[jointIndex] + deltaDeg;
        MoveJ(q);
    }

    public void Home(float[] qHomeDeg = null)
    {
        if (qHomeDeg == null || qHomeDeg.Length == 0)
        {
            qHomeDeg = new float[] { 0f, -30f, 60f, 0f, 30f, 0f };
        }
        MoveJ(qHomeDeg);
    }

    public float[] ReadCurrentQDeg()
    {
        var q = new float[joints.Count];
        for (int i = 0; i < joints.Count; i++)
        {
            q[i] = joints[i].xDrive.target;
        }
        return q;
    }

    public void ApplyJointTargets(float[] qDeg)
    {
        for (int i = 0; i < joints.Count; i++)
        {
            var d = joints[i].xDrive;
            d.target = qDeg[i];
            joints[i].xDrive = d;
        }
    }

    private static bool AllClose(float[] a, float[] b, float tol)
    {
        if (a.Length != b.Length) return false;
        for (int i = 0; i < a.Length; i++)
        {
            if (Mathf.Abs(Mathf.DeltaAngle(a[i], b[i])) > tol) return false;
        }
        return true;
    }

    // Perfil trapezoidal simple (grados)
    public static float TrapezoidDuration(float dq, float vmax, float amax)
    {
        dq = Mathf.Abs(dq);
        float tAcc = vmax / amax;
        float dAcc = 0.5f * amax * tAcc * tAcc;
        if (2f * dAcc >= dq)
        {
            // triangular
            return 2f * Mathf.Sqrt(dq / amax);
        }
        else
        {
            float dCruise = dq - 2f * dAcc;
            float tCruise = dCruise / vmax;
            return 2f * tAcc + tCruise;
        }
    }

    public static float TrapezoidPosition(float t, float q0, float qf, float vmax, float amax)
    {
        float dqSigned = Mathf.DeltaAngle(q0, qf);
        float sign = Mathf.Sign(dqSigned);
        float dq = Mathf.Abs(dqSigned);

        float tAcc = vmax / amax;
        float dAcc = 0.5f * amax * tAcc * tAcc;

        if (2f * dAcc >= dq)
        {
            float tPeak = Mathf.Sqrt(dq / amax);
            if (t <= tPeak)
            {
                float d = 0.5f * amax * t * t;
                return q0 + sign * d;
            }
            else
            {
                float t2 = t - tPeak;
                float d = 0.5f * amax * tPeak * tPeak + (amax * tPeak) * t2 - 0.5f * amax * t2 * t2;
                d = Mathf.Min(d, dq);
                return q0 + sign * d;
            }
        }
        else
        {
            float tCruise = (dq - 2f * dAcc) / vmax;
            float t1 = tAcc;
            float t2 = tAcc + tCruise;
            if (t <= t1)
            {
                float d = 0.5f * amax * t * t;
                return q0 + sign * d;
            }
            else if (t <= t2)
            {
                float d = dAcc + vmax * (t - t1);
                return q0 + sign * d;
            }
            else
            {
                float tau = t - t2;
                float d = dAcc + vmax * tCruise + (vmax * tau - 0.5f * amax * tau * tau);
                d = Mathf.Min(d, dq);
                return q0 + sign * d;
            }
        }
    }
}

