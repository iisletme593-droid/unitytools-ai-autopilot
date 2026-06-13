using UnityEngine;

namespace Gameplay
{
    /// Ses yöneticisi iskeleti: tek AudioSource üstünden tek-atım sesler.
    public class AudioManager : MonoBehaviour
    {
        public static AudioManager Instance { get; private set; }

        AudioSource _source;

        void Awake()
        {
            Instance = this;
            _source = gameObject.GetComponent<AudioSource>();
            if (_source == null) _source = gameObject.AddComponent<AudioSource>();
            _source.spatialBlend = 0f;
        }

        public void PlayOneShot(AudioClip clip, float volume = 1f)
        {
            if (clip != null) _source.PlayOneShot(clip, volume);
        }
    }
}
